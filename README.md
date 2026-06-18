# ⚖️ LexaAI — AI Legal Contract Analyzer

> An AI-powered full-stack web application that analyzes legal contracts, identifies risky clauses, scores overall risk, and answers natural-language questions about uploaded contracts — without needing a lawyer.

---

## 🔗 Links

|                      |                                                           |
| -------------------- | --------------------------------------------------------- |
| 🌐 **Live Demo**     | [lexaai.vercel.app](https://lexaai.vercel.app)            |
| 💻 **Frontend Repo** | [github.com/yourname/lexaai-frontend](https://github.com) |
| 🔧 **Backend Repo**  | [github.com/yourname/lexaai-backend](https://github.com)  |

---

## ✨ Features

- 📄 **Upload PDF contracts** for instant AI-powered analysis
- 🔍 **Clause extraction** — identifies unfair terms, missing protections, and liability traps
- 📊 **Risk scoring** — 0–10 risk score with color-coded visual breakdown
- 💬 **Ask AI** — chat with the contract using natural language Q&A
- 🔐 **JWT Authentication** — secure login/register with access + refresh token rotation
- 📑 **PDF Risk Report** — export a full formatted risk report
- 🌙 **Dark gold theme** — custom-designed auth UI with consistent design system

---

## 🖼️ Screenshots

| Login                                            | Upload                                             | Results                                              |
| ------------------------------------------------ | -------------------------------------------------- | ---------------------------------------------------- |
| ![Login](./lexaai/public/Screenshot%20login.png) | ![Upload](./lexaai/public/Screenshot%20upload.png) | ![Results](./lexaai/public/Screenshot%20result1.png) |

---

## 🛠️ Tech Stack

### Frontend

| Tech             | Purpose                                                     |
| ---------------- | ----------------------------------------------------------- |
| React 19 + Vite  | UI framework and dev server                                 |
| React Router DOM | Client-side routing                                         |
| Lucide React     | Icons                                                       |
| Axios            | HTTP client                                                 |
| Custom CSS       | Design system (no Tailwind components — pure CSS variables) |

### Backend

| Tech                         | Purpose                                      |
| ---------------------------- | -------------------------------------------- |
| FastAPI                      | REST API framework                           |
| LangChain + Groq (Llama 3.1) | LLM integration for contract analysis        |
| MongoDB + Motor              | Async database for user storage              |
| PyMuPDF                      | PDF text extraction                          |
| Python-Jose + Passlib        | JWT auth + bcrypt password hashing           |
| BM25-style TF-IDF search     | Lightweight contract chunk retrieval for Q&A |

---

## 📁 Project Structure

```
AI-contract-Analyser/
│
├── main.py                     # FastAPI app — routes: /upload, /ask
├── requirements.txt            # Python dependencies
│
├── auth/                       # Authentication module
│   ├── __init__.py
│   ├── routes.py               # /auth/register, /auth/login, /auth/refresh, /auth/logout, /auth/me
│   ├── utils.py                # JWT creation/decoding, password hashing
│   └── models.py               # MongoDB user document schema
│
└── lexaai/                     # React frontend
    ├── index.html
    ├── vite.config.js
    ├── package.json
    │
    └── src/
        ├── main.jsx            # App entry point, global CSS imports
        ├── App.jsx             # Root component, AuthProvider + ProtectedRoute
        ├── App.css             # Full design system (CSS variables, all component styles)
        ├── index.css           # Tailwind base + theme tokens
        │
        ├── components/
        │   ├── AuthPage.jsx    # Login + Register (single component, dual mode)
        │   ├── ProtectedRoute.jsx  # Guards dashboard behind auth
        │   ├── topbar.jsx      # Brand + user email + logout button
        │   ├── Upload.jsx      # Drag-and-drop PDF uploader
        │   ├── dashboard.jsx   # Results layout — wires metrics, clauses, ask, summary
        │   ├── metrics.jsx     # 4 metric cards (risk score, clauses, type, pages)
        │   ├── clauses.jsx     # Risk-coded clause list (high/medium/low)
        │   └── Panel.jsx       # Ask AI chat panel with message history
        │
        ├── hooks/
        │   ├── useAuth.jsx     # Auth context: login, logout, token refresh, auto-refresh
        │   └── ContractAnalysis.jsx  # Contract upload state management
        │
        ├── services/
        │   └── api.js          # fetch wrappers for /upload and /ask with JWT headers
        │
        └── styles/
            ├── login.css       # Dark gold auth theme
            └── register.css    # Register card overrides
```

---

## ⚙️ Local Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- MongoDB (local or Atlas)
- Groq API key — get one free at [console.groq.com](https://console.groq.com)

---

### 1. Clone the repo

```bash
git clone https://github.com/yourname/AI-contract-Analyser.git
cd AI-contract-Analyser
```

---

### 2. Backend setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Create .env file in the root
```

Create a `.env` file:

```env
MONGO_URI=mongodb://localhost:27017
JWT_SECRET=your-32-char-secret-here
API_KEY=your-groq-api-key-here
```

Generate a secure JWT secret:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Start the backend:

```bash
uvicorn main:app --reload --port 8000
```

Backend runs at → `http://localhost:8000`
API docs at → `http://localhost:8000/docs`

---

### 3. Frontend setup

```bash
cd lexaai

# Install dependencies
npm install

# Create .env file
echo "VITE_API_URL=http://localhost:8000" > .env

# Start dev server
npm run dev
```

Frontend runs at → `http://localhost:5173`

---

## 🔑 Environment Variables

### Backend (`.env` in project root)

| Variable     | Description                               | Example                     |
| ------------ | ----------------------------------------- | --------------------------- |
| `MONGO_URI`  | MongoDB connection string                 | `mongodb://localhost:27017` |
| `JWT_SECRET` | Secret key for JWT signing (min 32 chars) | `abc123...`                 |
| `API_KEY`    | Groq API key                              | `gsk_...`                   |

### Frontend (`lexaai/.env`)

| Variable       | Description      | Example                 |
| -------------- | ---------------- | ----------------------- |
| `VITE_API_URL` | Backend base URL | `http://localhost:8000` |

---

## 🔐 API Endpoints

### Auth

| Method | Endpoint         | Description                                       |
| ------ | ---------------- | ------------------------------------------------- |
| `POST` | `/auth/register` | Register new user                                 |
| `POST` | `/auth/login`    | Login, returns access token + sets refresh cookie |
| `POST` | `/auth/refresh`  | Get new access token using refresh cookie         |
| `POST` | `/auth/logout`   | Clear refresh token cookie                        |
| `GET`  | `/auth/me`       | Get current user info                             |

### Contract

| Method | Endpoint  | Auth        | Description                                        |
| ------ | --------- | ----------- | -------------------------------------------------- |
| `POST` | `/upload` | ✅ Required | Upload PDF, returns clauses + risk score + summary |
| `POST` | `/ask`    | ✅ Required | Ask a question about an uploaded contract          |

---

## 🚀 Deployment

| Part     | Platform                                   |
| -------- | ------------------------------------------ |
| Frontend | [Vercel](https://vercel.com)               |
| Backend  | [Railway](https://railway.app)             |
| Database | [MongoDB Atlas](https://cloud.mongodb.com) |

### Frontend (Vercel)

1. Push `lexaai/` to GitHub
2. Import repo on Vercel, set root directory to `lexaai`
3. Add environment variable: `VITE_API_URL=https://your-backend.railway.app`

### Backend (Railway)

1. Push backend folder to GitHub
2. New project on Railway → Deploy from GitHub
3. Add environment variables: `MONGO_URI`, `JWT_SECRET`, `API_KEY`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

---

## 📦 Key Dependencies

### Backend

```
fastapi          — REST API
uvicorn          — ASGI server
langchain-groq   — Groq LLM integration (Llama 3.1 8B)
langchain        — LLM orchestration
motor            — Async MongoDB driver
pymupdf          — PDF text extraction
python-jose      — JWT encoding/decoding
passlib[bcrypt]  — Password hashing
```

### Frontend

```
react            — UI library
vite             — Build tool and dev server
react-router-dom — Client-side routing
lucide-react     — Icon library
axios            — HTTP requests
```

---

## 🤝 Contributing

Pull requests are welcome. For major changes, open an issue first to discuss what you'd like to change.

---

## 📄 License

[MIT](./LICENSE)

---

## 👤 Author

**Your Name**

- GitHub: [@yourname](https://github.com/yourname)
- LinkedIn: [linkedin.com/in/yourname](https://linkedin.com/in/yourname)
- Email: your@email.com
