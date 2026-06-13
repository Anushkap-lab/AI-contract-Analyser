import asyncio
import base64
import hashlib
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from bson import ObjectId
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field, field_validator
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "AI_legal_analyser"
SECRET_KEY = os.getenv("KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7
ALLOWED_ORIGINS = ["http://localhost:5173", "http://localhost:5174",]
UPLOAD_DIR = Path("uploads")

sync_client = MongoClient(MONGO_URI)
sync_db = sync_client[DB_NAME]
users_collection = sync_db["users"]
chat_collection = sync_db["chat_history"]

async_client = AsyncIOMotorClient(MONGO_URI)

def get_async_db():
    return async_client[DB_NAME]

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
llm = ChatGroq(api_key=os.getenv("API_KEY"), model="llama-3.1-8b-instant", temperature=0.2)

contracts = {}

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def _pre_hash(plain: str) -> str:
    return base64.b64encode(hashlib.sha256(plain.encode()).digest()).decode()


def get_password_hash(password: str) -> str:
    return pwd_context.hash(_pre_hash(password))


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(_pre_hash(plain), hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + (expires_delta if expires_delta else timedelta(minutes=15))
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    return jwt.encode(
        {"sub": user_id, "type": "refresh", "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None


class TokenData(BaseModel):
    username: Optional[str] = None


class User(BaseModel):
    fullname: str
    email: Optional[str] = None
    disabled: Optional[bool] = None


class UserInDB(User):
    hashed_password: str


class RegisterRequest(BaseModel):
    fullname: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def strong_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError("Need at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Need at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Need at least one digit")
        return v


class RefreshRequest(BaseModel):
    refresh_token: str


class UserProfile(BaseModel):
    fullname: str
    email: Optional[str]
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None


class ChatRequest(BaseModel):
    contract_id: str
    question: str


async def get_user(identifier: str) -> Optional[dict]:
    return await get_async_db()["users"].find_one({"$or": [{"fullname": identifier}, {"email": identifier.lower()}]})


async def authenticate_user(identifier: str, password: str) -> Optional[dict]:
    user = await get_user(identifier)
    if not user or not verify_password(password, user["hashed_password"]):
        return None
    return user


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    exc = HTTPException(status.HTTP_401_UNAUTHORIZED, "Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise exc
    except JWTError:
        raise exc
    user = await get_user(username)
    if not user:
        raise exc
    return user


async def get_current_active_user(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("disabled"):
        raise HTTPException(400, "Inactive user")
    return current_user


async def invoke_llm(messages, error_label):
    try:
        return await llm.ainvoke(messages)
    except Exception as exc:
        raise HTTPException(502, f"{error_label} failed: {exc}") from exc


def parse_json_response(content, fallback):
    cleaned = content.strip().strip("`").strip()
    if cleaned.lower().startswith("json"):
        cleaned = cleaned[4:].strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return fallback


def normalize_clauses(clauses):
    normalized = []
    for clause in clauses:
        if not isinstance(clause, dict):
            continue
        risk = str(clause.get("risk", "medium")).lower().strip()
        category = str(clause.get("category", "unfair")).lower().strip()
        if "liability" in category:
            category = "liability"
        elif "missing" in category:
            category = "missing"
        else:
            category = "unfair"
        normalized.append({
            "name": clause.get("name") or "Contract issue",
            "description": clause.get("description") or "Review this issue carefully.",
            "risk": risk if risk in {"low", "medium", "high"} else "medium",
            "category": category,
        })
    return normalized


async def extract_clauses(text):
    messages = [
        SystemMessage(content="""You are a legal contract analyzer.
Extract important contract issues as JSON only.
Return a JSON array with keys: name, description, risk, category.
risk: low|medium|high. category: unfair|missing|liability."""),
        HumanMessage(content=f"Contract text:\n{text}"),
    ]
    response = await invoke_llm(messages, "Clause extraction")
    clauses = parse_json_response(response.content, [])
    return normalize_clauses(clauses) if isinstance(clauses, list) else []


async def calculate_risk(text):
    messages = [
        SystemMessage(content='You are a legal risk scoring engine. Return JSON only: {"score": number 0-10, "level": "Low Risk|Medium Risk|High Risk", "reason": "short reason"}'),
        HumanMessage(content=f"Contract text:\n{text}"),
    ]
    response = await invoke_llm(messages, "Risk scoring")
    risk = parse_json_response(response.content, {"score": 5, "level": "Medium Risk", "reason": response.content.strip()})
    if not isinstance(risk, dict):
        return {"score": 5, "level": "Medium Risk", "reason": str(risk)}
    try:
        risk["score"] = max(0, min(10, float(risk.get("score", 5))))
    except (TypeError, ValueError):
        risk["score"] = 5
    risk.setdefault("level", "Medium Risk")
    risk.setdefault("reason", "No reason returned.")
    return risk


async def generate_summary(text):
    messages = [
        SystemMessage(content="You are a legal contract analyzer. Write a concise plain English risk summary for a non-lawyer."),
        HumanMessage(content=f"Contract text:\n{text}"),
    ]
    response = await invoke_llm(messages, "Summary generation")
    return response.content.strip()


def format_clause_section(clauses, category, fallback):
    lines = [f"- {c.get('name','Clause')}: {c.get('description','').strip()}" for c in clauses if isinstance(c, dict) and c.get("category") == category]
    return "\n".join(lines) if lines else fallback


def build_analysis_report(summary, clauses, risk):
    return f"""1. Plain English risk summary\n{summary}\n\n2. Unfair clauses\n{format_clause_section(clauses, 'unfair', 'No unfair clauses identified.')}\n\n3. Missing terms\n{format_clause_section(clauses, 'missing', 'No missing terms identified.')}\n\n4. Liability traps\n{format_clause_section(clauses, 'liability', 'No liability traps identified.')}\n\n5. Overall risk score\n{risk['level']} - {risk['reason']}"""


def find_relevant_chunks_with_embeddings(contract, question, limit=4):
    vectorstore = contract.get("vectorstore")
    if not vectorstore:
        chunks = contract["chunks"]
        terms = {t.strip(".,;:!?()[]{}\"'").lower() for t in question.split() if len(t) > 2}
        scored = sorted(enumerate(chunks), key=lambda x: sum(1 for t in terms if t in x[1].lower()), reverse=True)
        return [c for _, c in scored[:limit]]
    return [d.page_content for d in vectorstore.similarity_search(question, k=limit)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = get_async_db()
    await db["users"].create_index("fullname", unique=True)
    await db["users"].create_index("email", unique=True)
    await db["refresh_tokens"].create_index("user_id")
    await db["refresh_tokens"].create_index("token")
    UPLOAD_DIR.mkdir(exist_ok=True)
    yield
    async_client.close()
app=FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.get("/")
def home():
    return {"message": "backend running"}


@app.get("/health")
def health():
    return {"status": "ok", "app": "AI Legal Analyzer"}


@app.post("/login", response_model=Token, tags=["Auth"])
async def login(body: LoginRequest) -> Any:
    user = await authenticate_user(body.email, body.password)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password", headers={"WWW-Authenticate": "Bearer"})
    access_token = create_access_token({"sub": user["fullname"]}, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    refresh_token = create_refresh_token(str(user["_id"]))
    await get_async_db()["refresh_tokens"].insert_one({"user_id": str(user["_id"]), "token": refresh_token, "created_at": datetime.now(timezone.utc)})
    await get_async_db()["users"].update_one({"_id": user["_id"]}, {"$set": {"last_login": datetime.now(timezone.utc)}})
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@app.post("/token", response_model=Token, tags=["Auth"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()) -> Any:
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})
    access_token = create_access_token({"sub": user["fullname"]}, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    refresh_token = create_refresh_token(str(user["_id"]))
    await get_async_db()["refresh_tokens"].insert_one({"user_id": str(user["_id"]), "token": refresh_token, "created_at": datetime.now(timezone.utc)})
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}




app = FastAPI()

@app.post("/register", status_code=201, tags=["Auth"])
async def register(body: RegisterRequest) -> dict:
    db = get_async_db() # ✅ await if it's a coroutine

    if not body.fullname or body.fullname.strip() == "":
        raise HTTPException(status_code=400, detail="Username is required")

    # ✅ These must be awaited — an unawaited coroutine is always truthy!
    if await db["users"].find_one({"fullname": body.fullname.strip()}):
        raise HTTPException(status_code=409, detail="Username already taken")

    if await db["users"].find_one({"email": body.email.lower()}):
        raise HTTPException(status_code=409, detail="Email already registered")

    now = datetime.now(timezone.utc)

    try:
        # ✅ Insert new user
        result = await db["users"].insert_one({
            "fullname": body.fullname.strip(),
            "email": body.email.lower(),
            "hashed_password": get_password_hash(body.password),
            "disabled": False,
            "created_at": now,
            "last_login": None
        })
    except DuplicateKeyError as e:
        # Handle duplicate key errors gracefully
        if "fullname" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already exists"
            )
        elif "email" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Duplicate key error"
            )

    # ✅ Generate tokens
    user_id = str(result.inserted_id)
    access_token = create_access_token(
        {"sub": body.fullname},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = create_refresh_token(user_id)

    # ✅ Save refresh token
    await db["refresh_tokens"].insert_one({
        "user_id": user_id,
        "token": refresh_token,
        "created_at": now
    })

    return {
        "message": "Account created successfully",
        "username": body.fullname,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }



@app.post("/auth/refresh", tags=["Auth"])
async def refresh_token(body: RefreshRequest) -> Any:
    exc = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")
    try:
        payload = jwt.decode(body.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise exc
        user_id = payload.get("sub")
    except JWTError:
        raise exc
    db = get_async_db()
    stored = await db["refresh_tokens"].find_one({"user_id": user_id, "token": body.refresh_token})
    if not stored:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token revoked")
    user = await db["users"].find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return {"access_token": create_access_token({"sub": user["fullname"]}, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)), "token_type": "bearer"}


@app.post("/auth/logout", tags=["Auth"])
async def logout(body: RefreshRequest, current_user: dict = Depends(get_current_active_user)) -> Any:
    await get_async_db()["refresh_tokens"].delete_many({"user_id": str(current_user["_id"])})
    return {"message": "Logged out successfully"}


@app.get("/users/me/", response_model=User, tags=["Users"])
async def read_users_me(current_user: dict = Depends(get_current_active_user)) -> Any:
    return User(fullname=current_user["fullname"], email=current_user.get("email"), disabled=current_user.get("disabled"))


@app.get("/users/me/profile", response_model=UserProfile, tags=["Users"])
async def get_profile(current_user: dict = Depends(get_current_active_user)) -> Any:
    return UserProfile(fullname=current_user.get("fullname"), email=current_user.get("email"), is_active=not current_user.get("disabled", False), created_at=current_user["created_at"], last_login=current_user.get("last_login"))


@app.post("/upload", tags=["Contracts"])
async def upload_contract(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "No file was uploaded.")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Please upload a PDF contract.")
    safe_name = Path(file.filename).name
    file_location = UPLOAD_DIR / f"{uuid4().hex}_{safe_name}"
    with open(file_location, "wb") as buffer:
        while chunk := await file.read(1024 * 1024):
            buffer.write(chunk)
    try:
        documents = PyMuPDFLoader(str(file_location)).load()
    except Exception as exc:
        raise HTTPException(400, f"Could not read PDF: {exc}") from exc
    text = "".join(doc.page_content for doc in documents)
    if not text.strip():
        raise HTTPException(400, "The uploaded PDF has no readable text.")
    docs = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=200).create_documents([text])
    contract_id = uuid4().hex
    try:
        vectorstore = FAISS.from_documents(docs, embeddings)
    except Exception as exc:
        raise HTTPException(502, f"Could not create embeddings: {exc}") from exc
    contracts[contract_id] = {"filename": file.filename, "chunks": [doc.page_content for doc in docs], "vectorstore": vectorstore}
    clauses, risk, summary = await asyncio.gather(extract_clauses(text), calculate_risk(text), generate_summary(text))
    return {"contractId": contract_id, "filename": file.filename, "clauses": clauses, "riskScore": risk["score"], "summary": summary, "analysis": [build_analysis_report(summary, clauses, risk)]}


@app.post("/ask", tags=["Contracts"])
async def ask_contract(request: ChatRequest):
    if not request.question.strip():
        raise HTTPException(400, "Please enter a question.")
    contract = contracts.get(request.contract_id)
    if not contract:
        raise HTTPException(404, "Contract not found. Please upload the contract again.")
    try:
        relevant_chunks = find_relevant_chunks_with_embeddings(contract, request.question)
    except Exception as exc:
        raise HTTPException(502, f"Embedding search failed: {exc}") from exc
    excerpts = "\n\n---\n\n".join(relevant_chunks)
    messages = [
        SystemMessage(content="You answer questions about a legal contract using only the provided excerpts. Keep answers concise and practical."),
        HumanMessage(content=f"Question: {request.question}\n\nContract excerpts:\n{excerpts}"),
    ]
    try:
        response = llm.invoke(messages)
    except Exception as exc:
        raise HTTPException(502, f"AI question answering failed: {exc}") from exc
    return {"answer": response.content}
