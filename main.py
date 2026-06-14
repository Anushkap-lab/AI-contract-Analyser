# main.py
import asyncio
import json
import logging
import os
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
load_dotenv()   # ← must be FIRST before any os.getenv calls

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials
from langchain_groq import ChatGroq
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel


from auth.routes import router as auth_router, get_current_user

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,   
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)   


UPLOAD_DIR = Path("uploads")
contracts  = {}   

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

llm = ChatGroq(
    api_key=os.getenv("API_KEY"),
    model="llama-3.1-8b-instant",
    temperature=1,
)

# ── Schemas ────────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    contract_id: str
    question:    str

# ── LLM helpers ───────────────────────────────────────────────────────────────
async def invoke_llm(messages, error_label):
    try:
        return await llm.ainvoke(messages)
    except Exception as exc:
        raise HTTPException(502, f"{error_label} failed: {exc}") from exc

def parse_json_response(content, fallback):
    cleaned = content.strip().strip("`")
    if cleaned.lower().startswith("json"):
        cleaned = cleaned[4:].strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return fallback

def normalize_clauses(clauses):
    normalized = []
    valid_risks      = {"low", "medium", "high"}
    valid_categories = {"unfair", "missing", "liability"}
    for clause in clauses:
        if not isinstance(clause, dict):
            continue
        risk     = str(clause.get("risk", "medium")).lower().strip()
        category = str(clause.get("category", "unfair")).lower().strip()
        if "liability" in category:   category = "liability"
        elif "missing" in category:   category = "missing"
        else:                         category = "unfair"
        normalized.append({
            "name":        clause.get("name") or "Contract issue",
            "description": clause.get("description") or "Review this issue carefully.",
            "risk":        risk if risk in valid_risks else "medium",
            "category":    category if category in valid_categories else "unfair",
        })
    return normalized

async def extract_clauses(text):
    messages = [
        SystemMessage(content="""You are a legal contract analyzer.
Extract important contract issues as JSON only.
Return a JSON array of objects with exactly these keys: name, description, risk, category.
risk must be one of: low, medium, high.
category must be one of: unfair, missing, liability."""),
        HumanMessage(content=f"Contract text:\n{text}"),
    ]
    response = await invoke_llm(messages, "Clause extraction")
    clauses  = parse_json_response(response.content, [])
    return normalize_clauses(clauses) if isinstance(clauses, list) else []

async def calculate_risk(text):
    messages = [
        SystemMessage(content="""You are a legal contract risk scoring engine.
Return JSON only: {"score": number, "level": "Low Risk|Medium Risk|High Risk", "reason": "short reason"}
The score must be 0–10."""),
        HumanMessage(content=f"Contract text:\n{text}"),
    ]
    response = await invoke_llm(messages, "Risk scoring")
    risk     = parse_json_response(
        response.content,
        {"score": 5, "level": "Medium Risk", "reason": response.content.strip()},
    )
    if not isinstance(risk, dict):
        return {"score": 5, "level": "Medium Risk", "reason": str(risk)}
    try:
        risk["score"] = max(0, min(10, float(risk.get("score", 5))))
    except (TypeError, ValueError):
        risk["score"] = 5
    return risk

async def generate_summary(text):
    messages = [
        SystemMessage(content="""You are a legal contract analyzer.
Write a concise plain English risk summary for a non-lawyer.
Focus on practical business risks."""),
        HumanMessage(content=f"Contract text:\n{text}"),
    ]
    response = await invoke_llm(messages, "Summary generation")
    return response.content.strip()

def build_analysis_report(summary, clauses, risk):
    def section(cat, fallback):
        lines = [
            f"- {c.get('name')}: {c.get('description','').strip()}"
            for c in clauses if isinstance(c, dict) and c.get("category") == cat
        ]
        return "\n".join(lines) if lines else fallback

    return f"""1. Plain English risk summary
{summary}

2. Unfair clauses
{section("unfair", "No unfair clauses identified.")}

3. Missing terms
{section("missing", "No missing terms identified.")}

4. Liability traps
{section("liability", "No liability traps identified.")}

5. Overall risk score
{risk["level"]} - {risk["reason"]}"""

# ── Routes ─────────────────────────────────────────────────────────────────────
@app.get("/")
def home():
    return {"message": "backend running"}


@app.post("/upload")
async def upload_contract(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),   # ← protected
):
    if not file.filename:
        raise HTTPException(400, "No file uploaded.")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Please upload a PDF contract.")

    UPLOAD_DIR.mkdir(exist_ok=True)
    safe_name     = Path(file.filename).name
    file_location = UPLOAD_DIR / f"{uuid4().hex}_{safe_name}"

    with open(file_location, "wb") as buffer:
        while chunk := await file.read(1024 * 1024):
            buffer.write(chunk)

    try:
        loader    = PyMuPDFLoader(str(file_location))
        documents = loader.load()
    except Exception as exc:
        raise HTTPException(400, f"Could not read PDF: {exc}") from exc

    text = "".join(doc.page_content for doc in documents)
    if not text.strip():
        raise HTTPException(400, "PDF has no readable text.")

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=200)
    docs     = splitter.create_documents([text])

    contract_id = uuid4().hex
    try:
        vectorstore = FAISS.from_documents(docs, embeddings)
    except Exception as exc:
        raise HTTPException(502, f"Could not create embeddings: {exc}") from exc

    contracts[contract_id] = {
        "filename":   file.filename,
        "chunks":     [doc.page_content for doc in docs],
        "vectorstore": vectorstore,
        "user_id":    str(current_user["_id"]),   # track which user uploaded
    }

    clauses, risk, summary = await asyncio.gather(
        extract_clauses(text),
        calculate_risk(text),
        generate_summary(text),
    )
    final_report = build_analysis_report(summary, clauses, risk)

    return {
        "contractId": contract_id,
        "filename":   file.filename,
        "clauses":    clauses,
        "riskScore":  risk["score"],
        "summary":    summary,
        "analysis":   [final_report],
    }


def find_relevant_chunks_with_embeddings(contract, question, limit=4):
    vectorstore = contract.get("vectorstore")
    if not vectorstore:
        chunks = contract["chunks"]
        terms  = {t.lower() for t in question.split() if len(t) > 2}
        scored = sorted(chunks, key=lambda c: sum(1 for t in terms if t in c.lower()), reverse=True)
        return scored[:limit]
    docs = vectorstore.similarity_search(question, k=limit)
    return [doc.page_content for doc in docs]


@app.post("/ask")
async def ask_contract(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),   # ← protected
):
    if not request.question.strip():
        raise HTTPException(400, "Please enter a question.")

    contract = contracts.get(request.contract_id)
    if not contract:
        raise HTTPException(404, "Contract not found. Please upload again.")

    try:
        chunks = find_relevant_chunks_with_embeddings(contract, request.question)
    except Exception as exc:
        raise HTTPException(502, f"Embedding search failed: {exc}") from exc

    excerpts = "\n\n---\n\n".join(chunks)
    messages = [
        SystemMessage(content="""You answer questions about an uploaded legal contract.
Use only the provided contract excerpts.
If not enough info, say so. Keep answers concise."""),
        HumanMessage(content=f"Question: {request.question}\n\nContract excerpts:\n{excerpts}"),
    ]
    try:
        response = await llm.ainvoke(messages)
    except Exception as exc:
        raise HTTPException(502, f"AI question answering failed: {exc}") from exc

    return {"answer": response.content}
