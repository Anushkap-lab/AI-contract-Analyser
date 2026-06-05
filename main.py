import asyncio
import json
import logging
import os
import re
from pathlib import Path
from uuid import uuid4
from dotenv import load_dotenv
from pymongo import MongoClient
from langchain_groq import ChatGroq
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.messages import SystemMessage,HumanMessage,AIMessage
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from fastapi import APIRouter, FastAPI, UploadFile, File, HTTPException,status
from fastapi.middleware.cors import CORSMiddleware

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, EmailStr, Field,field_validator
from datetime import timezone,datetime,timedelta
from passlib.context import CryptContext
from jose import jwt

load_dotenv()
app=FastAPI()
router = APIRouter(prefix="/auth", tags=["auth"])
UPLOAD_DIR = Path("uploads")
mongo_uri=os.getenv("MONGO_URI")
contracts = {}
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")




client = MongoClient(mongo_uri)
db = client["AI_legal_analyser"]
users_collection = db["users"]
chat_collection = db["chat_history"]

api = os.getenv("API_KEY")
llm=ChatGroq(
    api_key = api,
    model="llama-3.1-8b-instant",
    temperature=1,
  
 
   

)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174","http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




class ChatRequest(BaseModel):
    contract_id:str
    question:str


async def invoke_llm(messages, error_label):
    try:
        return await llm.ainvoke(messages)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"{error_label} failed: {exc}",
        ) from exc


def parse_json_response(content, fallback):
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return fallback


def normalize_clauses(clauses):
    normalized = []
    valid_risks = {"low", "medium", "high"}
    valid_categories = {"unfair", "missing", "liability"}

    for clause in clauses:
        if not isinstance(clause, dict):
            continue

        risk = str(clause.get("risk", "medium")).lower().strip()
        category = str(clause.get("category", "unfair")).lower().strip()
        if "liability" in category:
            category = "liability"
        elif "missing" in category:
            category = "missing"
        elif "unfair" in category:
            category = "unfair"

        normalized.append({
            "name": clause.get("name") or "Contract issue",
            "description": clause.get("description") or "Review this issue carefully.",
            "risk": risk if risk in valid_risks else "medium",
            "category": category if category in valid_categories else "unfair",
        })

    return normalized


async def extract_clauses(text):
    messages = [
        SystemMessage(content="""You are a legal contract analyzer.
        Extract important contract issues as JSON only.
        Return a JSON array of objects with exactly these keys:
        name, description, risk, category.
        risk must be one of: low, medium, high.
        category must be one of: unfair, missing, liability.
        Keep descriptions concise and practical."""),
        HumanMessage(content=f"Contract text:\n{text}"),
    ]
    response = await invoke_llm(messages, "Clause extraction")
    clauses = parse_json_response(response.content, [])
    return normalize_clauses(clauses) if isinstance(clauses, list) else []


async def calculate_risk(text):
    messages = [
        SystemMessage(content="""You are a legal contract risk scoring engine.
        Return JSON only in this exact shape:
        {"score": number, "level": "Low Risk|Medium Risk|High Risk", "reason": "short reason"}
        The score must be from 0 to 10."""),
        HumanMessage(content=f"Contract text:\n{text}"),
    ]
    response = await invoke_llm(messages, "Risk scoring")
    risk = parse_json_response(
        response.content,
        {"score": 5, "level": "Medium Risk", "reason": response.content.strip()},
    )
    if not isinstance(risk, dict):
        return {"score": 5, "level": "Medium Risk", "reason": str(risk)}

    try:
        risk["score"] = max(0, min(10, float(risk.get("score", 5))))
    except (TypeError, ValueError):
        risk["score"] = 5

    risk["level"] = risk.get("level") or "Medium Risk"
    risk["reason"] = risk.get("reason") or "No short reason returned."
    return risk


async def generate_summary(text):
    messages = [
        SystemMessage(content="""You are a legal contract analyzer.
        Write a concise plain English risk summary for a non-lawyer.
        Focus on the practical business risks and avoid repeating clause text."""),
        HumanMessage(content=f"Contract text:\n{text}"),
    ]
    response = await invoke_llm(messages, "Summary generation")
    return response.content.strip()


def format_clause_section(clauses, category, fallback):
    lines = [
        f"- {clause.get('name', 'Clause')}: {clause.get('description', '').strip()}"
        for clause in clauses
        if isinstance(clause, dict) and clause.get("category") == category
    ]
    return "\n".join(lines) if lines else fallback


def build_analysis_report(summary, clauses, risk):
    return f"""1. Plain English risk summary
{summary}

2. Unfair clauses
{format_clause_section(clauses, "unfair", "No unfair clauses were identified.")}

3. Missing terms
{format_clause_section(clauses, "missing", "No missing terms were identified.")}

4. Liability traps
{format_clause_section(clauses, "liability", "No liability traps were identified.")}

5. Overall risk score
{risk["level"]} - {risk["reason"]}"""


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
    clauses, risk, summary = await asyncio.gather(
        extract_clauses(text),
        calculate_risk(text),
        generate_summary(text),
    )
    final_report = build_analysis_report(summary, clauses, risk)
    
    return {
        "contractId": contract_id,
        "filename": file.filename,
        "clauses": clauses,
        "riskScore": risk["score"],
        "summary": summary,
        "analysis": [final_report]
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
    chats=chat_collection.find({"user_id":user_id}).sort("timestamp",1)
    history=[]

    for chat in chats:
        history.append((chat["role"],chat["message"]))
    return history


def chat(request:ChatRequest):
        history=get_history(request.user_id)
        response = llm.invoke({"history":history,"question":request.question})
        chat_collection.insert_one({
            "user_id":request.user_id,
            "role":"user",
            "message": request.question,
            "timestamp":datetime.now(timezone.utc)
         })
        chat_collection.insert_one({
            "user_id":request.user_id,
            "role":"assistant",
            "message": response.content,
            "timestamp":datetime.now(timezone.utc)
        })

        return {"response":response.content}
#login 
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Schemas ---
class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    company_size: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        return v

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        return v


class RegisterResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    message: str


# --- Endpoint ---
@app.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(payload: RegisterRequest):
    # Check if email already exists
    if users_collection.find_one({"email": payload.email}):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    # Hash password
    hashed_password = pwd_context.hash(payload.password)

    # Build user document
    user_doc = {
        "first_name": payload.first_name,
        "last_name": payload.last_name,
        "email": payload.email,
        "password": hashed_password,
        "company_size": payload.company_size,
        "is_verified": False,
        "created_at": datetime.utcnow(),
    }

    result = users_collection.insert_one(user_doc)

    return RegisterResponse(
        id=str(result.inserted_id),
        email=payload.email,
        first_name=payload.first_name,
        last_name=payload.last_name,
        message="Account created successfully",
    )

SECRET_KEY=os.getenv("JWT_KEY")


def create_access_token(email):

    payload={
      "sub":email,
      "exp": datetime.now(timezone.utc) + timedelta(days=1)

    }
    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm="HS256"
    )
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
@app.post("/login")
def login(data: LoginRequest):
    user = users_collection.find_one({"email": data.email})


    if not user or not verify_password(data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    return {"token": create_access_token(data.email)}