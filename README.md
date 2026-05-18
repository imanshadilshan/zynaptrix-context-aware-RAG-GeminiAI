# Zynaptrix Context-Aware RAG & Multi-Agent Assistant Platform

Welcome to the **Zynaptrix Standalone Context-Aware RAG and Multi-Agent Chat Assistant Platform**! 

This self-sufficient engineering platform specializes in **parsing complex industrial technical manuals, segmenting schematics via SAM models, captioning sub-diagrams, auditing safety guidelines (LOTO/PPE), and compiling stateful diagnostic checklists** into high-fidelity printable reports using **Google Gemini 2.5 Pro & Flash** models. 

---

## 🌌 System Architecture

```mermaid
graph TD
    A[Next.js Frontend Workspace] -->|1. Ingest PDF Manual| B(FastAPI Ingestion Endpoint)
    A -->|2. Send Stateful Inquiry| C(FastAPI Assistant API)
    
    subgraph "Ingestion Core"
        B --> D[PyMuPDF & YOLO Layout Parser]
        D -->|Extract Figures| E[Gemini & Mobile SAM figure splitter]
        D -->|Extract Tables| F[Camelot & Gemini transformer]
        D -->|Extract Text| G[Recursive LangChain splittings]
        E & F & G --> H[Gemini text-embedding-004]
        H -->|Save Vectors| I[(Neon DB pgvector OR SQLite Fallback)]
    end
    
    subgraph "Orchestration & RAG retrieval"
        C --> J[Orchestrator Agent]
        J -->|Dual similarity search| K[Retrieval Engine]
        K -->|Query Context| I
        J -->|LOTO / PPE audits| L[Safety Critic Agent]
        J -->|Compile Guide| M[Knowledge Agent]
        J -->|JSON incident summary| N[Report Writer Agent]
        L & M & N -->|Consolidated Answer| A
    end
```

---

## ✨ Key Features

1. **Full-Fidelity Document Ingestion**:
   * Uses **PyMuPDF** and **YOLOv8 DocLayNet** to isolate layout segments (headers, paragraphs, figures, tables).
   * Employs **Gemini 2.5 Flash** for sub-diagram center detection and **Mobile SAM** to generate neural segment masks.
   * Leverages **Gemini Vision** for engineering-grade technical captioning of isolated diagram crops.
   * Maps tables via **Camelot** and generates concise vector-ready JSON table summaries.

2. **Modular Multi-Agent Cognitive Orchestrator**:
   * **Orchestrator Agent**: Scopes context histories and dynamically classifies dialogues (ONBOARDING, CHAT, GUIDE, REPORT, RAG).
   * **Knowledge Agent**: Compiles vectorized manual excerpts and inserts dynamic `[IMAGE_N]` reference anchors matching layout figures.
   * **Safety Critic Agent**: Reviews procedures to ensure vital LOTO and PPE bold warning checkmarks are highlighted at the top of instructions.
   * **Report Writer Agent**: Transforms conversational histories into fully structured JSON diagnostics.

3. **Dual Vector Database Similarity Fallback**:
   * **Neon PostgreSQL**: Performs native database-level vector similarity searches using `pgvector` operators.
   * **Local SQLite**: Pulls candidate manual text-chunks, deserializes their stored vector strings, and computes **in-memory cosine similarity via NumPy matrix dot-products**—enabling 100% parity during local offline development.

4. **Premium Space-Themed Dashboard**:
   * Designed with Next.js 16, Redux Toolkit client states, and stunning starfield canvas animations.
   * Interactive checklists enabling operators to check off repair steps or click "Stuck" to request alternative guidelines.
   * High-fidelity client-side PDF Report Exporter producing custom A4 coverpages, badges, watermarks, and embedded base64-converted SAM diagram crops.

---

## 📁 Repository Layout

```bash
Context-Aware-RAG-GeminiAI/
├── backend/                  # FastAPI Application
│   ├── agents/               # Specialized Gemini AI Agents
│   ├── app/                  # FastAPI routers and app server entrypoints
│   ├── models/               # Pretrained weights (SAM/YOLO) & database schemas
│   ├── services/             # Multimodal crop services & Cloud CDN syncs
│   ├── unified_rag/          # Core RAG, Embeddings, Ingestion, and DB setup
│   ├── .env.example          # Clean configuration template
│   └── requirements.txt      # Python libraries
│
└── frontend/                 # Next.js 16 Web Dashboard
    ├── src/
    │   ├── app/              # Next.js App Routing Pages
    │   ├── components/       # Sidebars, Selectors, and backgrounds
    │   ├── store/            # Redux state providers and slices
    │   └── professionalReportService.ts  # Premium PDF Generator
    ├── .env.example          # Client-side configuration template
    └── package.json          # Node dependencies
```

---

## 🚀 Execution & Setup Guide

### 1. Backend Server

#### Environment Setup
Copy and populate the environment file inside `backend/`:
```powershell
cd backend
copy .env.example .env
```

Edit `.env` with your credentials:
```env
DATABASE_URL=postgresql://neondb_owner:YOUR_PASS@YOUR_NEON_HOST.us-east-1.aws.neon.tech/neondb?sslmode=require
GEMINI_API_KEY=AIzaSy...
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
API_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
LOG_LEVEL=INFO
```

> If `DATABASE_URL` is left blank, the system automatically falls back to a local SQLite database.

#### Create Virtual Environment & Install Dependencies
Run these once from inside the `backend/` directory:

```powershell
python -m venv .venv
```

Activate the environment:

| Shell | Command |
|-------|---------|
| **Windows PowerShell** | `.\.venv\Scripts\Activate.ps1` |
| **Windows CMD** | `.\.venv\Scripts\activate.bat` |
| **Git Bash / macOS / Linux** | `source .venv/Scripts/activate` |

> If PowerShell blocks activation, first run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process`

Install dependencies:
```bash
pip install -r requirements.txt
```

#### Launch the Backend
Run from inside the `backend/` directory with the venv active:

**Windows PowerShell:**
```powershell
$env:PYTHONUTF8 = "1"
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Git Bash / macOS / Linux:**
```bash
PYTHONUTF8=1 uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

> `PYTHONUTF8=1` is required on Windows to prevent encoding errors from emoji characters in log output.

The API will be available at **`http://127.0.0.1:8000`**  
Interactive API docs (Swagger UI): **`http://127.0.0.1:8000/docs`**

---

### 2. Frontend Dashboard

#### Environment Setup
From inside the `frontend/` directory:
```powershell
copy .env.example .env
```

Edit `.env`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

#### Install & Run
```powershell
npm install
npm run dev
```

Open **`http://localhost:3000`** in your browser to interact with the Zynaptrix platform!

---

## 🏆 Development Checkpoints

* **100% TypeScript Compliance**: Bundles successfully via Next.js Turbopack compiler (`npm run build`).
* **100% Python Compilation**: Evaluates cleanly across all orchestrator files (`python -m py_compile`).
* **Rate-Limit Guardrails**: Integrates Semaphore Rate-Limit locks within RAG ingestion parallel tasks to prevent Gemini API quota exhaustion.
