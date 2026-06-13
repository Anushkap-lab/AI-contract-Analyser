import asyncio
import base64
import hashlib
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
from langchain_core.messages import SystemMessage,HumanMessage
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from fastapi import APIRouter, FastAPI, UploadFile, File, HTTPException,status,Depends
from fastapi.middleware.cors import CORSMiddleware

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, EmailStr, Field,field_validator
from datetime import timezone,datetime,timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
from contextlib import asynccontextmanager
from typing import Any, Optional
 
from bson import ObjectId
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm




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

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id            = Column(Integer, primary_key=True, index=True)
    email         = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name     = Column(String)
    created_at    = Column(DateTime, default=datetime.utcnow)

from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os

SECRET_KEY    = os.environ["JWT_SECRET"]   # set in .env — keep this secret!
ALGORITHM     = "HS256"
ACCESS_EXPIRE = 15          # minutes
REFRESH_EXPIRE = 60 * 24 * 7  # 7 days in minutes

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_ctx.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)

def create_token(data: dict, expires_minutes: int) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=expires_minutes)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def create_access_token(user_id: int, email: str) -> str:
    return create_token(
        {"sub": str(user_id), "email": email, "type": "access"},
        ACCESS_EXPIRE
    )

def create_refresh_token(user_id: int) -> str:
    return create_token(
        {"sub": str(user_id), "type": "refresh"},
        REFRESH_EXPIRE
    )

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
    
