import os
from pathlib import Path
from uuid import uuid4
from dotenv import load_dotenv
from pymongo import MongoClient
from langchain_groq import ChatGroq
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.messages import SystemMessage,HumanMessage,AIMessage
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel
from datetime import timezone,datetime
load_dotenv()
app=FastAPI()
UPLOAD_DIR = Path("uploads")
mongo_uri=os.getenv("MONGO_URI")
contracts = {}
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")




client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
db = client["AI_legal_analyser"]
collection = db["users"]

api = os.getenv("API_KEY")
llm=ChatGroq(
    api_key = api,
    model="llama-3.1-8b-instant",
    temperature=1,
  
 
   

)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




class ChatRequest(BaseModel):
    contract_id:str
    question:str



@app.get("/")
def home():
    return {"message":"backend running"}




@app.post("/upload")
async def upload_contract(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file was uploaded.")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF contract.")

    UPLOAD_DIR.mkdir(exist_ok=True)
    safe_name = Path(file.filename).name
    file_location = UPLOAD_DIR / f"{uuid4().hex}_{safe_name}"

    
    with open(file_location, "wb") as buffer:

        while chunk := await file.read(1024 * 1024):
            buffer.write(chunk)


    try:
        loader = PyMuPDFLoader(str(file_location))
        documents = loader.load()
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not read the uploaded PDF: {exc}",
        ) from exc

    text=""
    for doc in documents:
        text+=doc.page_content

    if not text.strip():
        raise HTTPException(status_code=400, detail="The uploaded PDF has no readable text.")

    splitter=RecursiveCharacterTextSplitter(
        chunk_size= 500,
        chunk_overlap=200
    )
    docs=splitter.create_documents([text])

    contract_id = uuid4().hex
    try:
        vectorstore = FAISS.from_documents(docs, embeddings)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not create contract embeddings: {exc}",
        ) from exc

    contracts[contract_id] = {
        "filename": file.filename,
        "chunks": [doc.page_content for doc in docs],
        "vectorstore": vectorstore,
    }
    chunk_notes = []

    for chunk in docs:
        messages=[
            SystemMessage(content="""you are legal contract analyzer 
            Extract only the important findings from this contract section.
            Do not write a full report.
            Do not repeat headings like plain English risk summary.
            Focus on:
            - unfair clauses
            - missing terms
            - liability traps
            - risk signals"""),
            HumanMessage(content=f"Contract section:{chunk.page_content} ")
            ]

        try:
            response = llm.invoke(messages)
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"AI analysis failed: {exc}",
            ) from exc
        chunk_notes.append(response.content)

    final_messages = [
        SystemMessage(content="""you are legal contract analyzer.
        Create one final consolidated contract analysis report from the notes.
        Write each section only once:
        1. Plain English risk summary
        2. Unfair clauses
        3. Missing terms
        4. Liability traps
        5. Overall risk score: Low Risk, Medium Risk, or High Risk
        Be concise and avoid repeating the same point."""),
        HumanMessage(content="\n\n".join(chunk_notes))
    ]

    try:
        final_response = llm.invoke(final_messages)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Final AI analysis failed: {exc}",
        ) from exc
    
    return {
        "contractId": contract_id,
        "filename": file.filename,
        "analysis": [final_response.content]
    }


def find_relevant_chunks(chunks, question, limit=4):
    question_terms = {
        term.strip(".,;:!?()[]{}\"'").lower()
        for term in question.split()
        if len(term.strip(".,;:!?()[]{}\"'")) > 2
    }

    scored_chunks = []
    for index, chunk in enumerate(chunks):
        lower_chunk = chunk.lower()
        score = sum(1 for term in question_terms if term in lower_chunk)
        scored_chunks.append((score, index, chunk))

    scored_chunks.sort(key=lambda item: (-item[0], item[1]))
    selected = [chunk for score, _, chunk in scored_chunks[:limit] if score > 0]
    return selected or chunks[:limit]


def find_relevant_chunks_with_embeddings(contract, question, limit=4):
    vectorstore = contract.get("vectorstore")
    if not vectorstore:
        return find_relevant_chunks(contract["chunks"], question, limit)

    docs = vectorstore.similarity_search(question, k=limit)
    return [doc.page_content for doc in docs]


@app.post("/ask")
async def ask_contract(request: ChatRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Please enter a question.")

    contract = contracts.get(request.contract_id)
    if not contract:
        raise HTTPException(
            status_code=404,
            detail="Contract not found. Please upload the contract again.",
        )

    try:
        relevant_chunks = find_relevant_chunks_with_embeddings(contract, request.question)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Embedding search failed: {exc}",
        ) from exc

    excerpts = "\n\n---\n\n".join(relevant_chunks)
    messages = [
        SystemMessage(content="""You answer questions about an uploaded legal contract.
        Use only the provided contract excerpts.
        If the excerpts do not contain enough information, say that the contract text provided does not answer it.
        Keep the answer concise and practical."""),
        HumanMessage(
            content=(
                f"Question: {request.question}\n\n"
                f"Contract excerpts:\n{excerpts}"
            )
        ),
    ]

    try:
        response = llm.invoke(messages)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"AI question answering failed: {exc}",
        ) from exc

    return {"answer": response.content}

def get_history(user_id):
    chats=collection.find({"user_id":user_id}).sort("timestamp",1)
    history=[]

    for chat in chats:
        history.append((chat["role"],chat["message"]))
    return history


def chat(request:ChatRequest):
        history=get_history(request.user_id)
        response = llm.invoke({"history":history,"question":request.question})
        collection.insert_one({
            "user_id":request.user_id,
            "role":"user",
            "message": request.question,
            "timestamp":datetime.now(timezone.utc)
         })
        collection.insert_one({
            "user_id":request.user_id,
            "role":"assistant",
            "message": response.content,
            "timestamp":datetime.now(timezone.utc)
        })

        return {"response":response.content}


