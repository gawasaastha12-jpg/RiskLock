# 🔒 RiskLock

**A secure, real-time financial risk assessment platform.**

RiskLock evaluates transactions against configurable risk thresholds, flags anomalies, and gives operators a fast, auditable way to approve, reject, or investigate financial activity — all backed by a hardened FastAPI service and a responsive React dashboard.

> ⚠️ **Note:** Replace this tagline and the "What it does" section below with an accurate description of your core assessment logic if it differs — this README assumes a transaction-risk-scoring use case based on the project's existing `/assess` endpoint, balance/amount validation, and audit logging.

---

## ✨ Features

- **Real-time transaction assessment** via a single `/assess` endpoint, with strict input bounds (no negative amounts, no unbounded values)
- **Operator authentication** with salted PBKDF2-HMAC-SHA256 password hashing (600,000 iterations) — no plaintext, no shortcuts
- **Signed, revocable session tokens** delivered via `HttpOnly`, `Secure`, `SameSite=Strict` cookies — immune to XSS token theft and CSRF
- **Brute-force protection** with per-IP rate limiting and automatic account lockout after repeated failed logins
- **Full audit trail** with automatic redaction of sensitive fields (passwords, tokens, secrets) before anything touches disk
- **Production-grade HTTP hardening**: CSP, HSTS, clickjacking protection, MIME-sniffing prevention, and strict payload size limits
- **Zero hardcoded credentials in production** — demo accounts are environment-gated and disabled by default

---

## 🏗️ Architecture

```
risklock/
├── main.py                 # FastAPI backend — auth, assessment logic, security middleware
├── requirements.txt        # Python dependencies
├── logs/
│   ├── audit_log.jsonl     # Sanitized, append-only audit log
│   └── registered_users.json  # Hashed + salted user credentials
├── frontend_v2/
│   ├── src/
│   │   └── AuthPage.tsx    # Login / session handling UI
│   ├── package.json
│   └── .env.example
├── .env.example
└── render.yaml             # Render Blueprint (backend + frontend services)
```

**Stack:**
| Layer | Technology |
|---|---|
| Backend | FastAPI (Python) |
| Frontend | React + Vite + TypeScript |
| Auth | PBKDF2-HMAC-SHA256, HMAC-signed session tokens |
| Styling | Tailwind CSS |
| Hosting | Render (Web Service + Static Site) |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- `pip` and `npm`

### 1. Clone and configure environment variables

```bash
git clone <your-repo-url>
cd risklock
cp .env.example .env
cp frontend_v2/.env.example frontend_v2/.env
```

Generate a secure session secret:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Paste the result into `.env` as `SESSION_SECRET_KEY`.

### 2. Run the backend

```bash
pip install -r requirements.txt --break-system-packages
uvicorn main:app --reload --port 8000
```

### 3. Run the frontend

```bash
cd frontend_v2
npm install
npm run dev
```

The app will be available at `http://localhost:5173` (frontend) and `http://localhost:8000` (API).

---

## 🔑 Environment Variables

| Variable | Description | Required |
|---|---|---|
| `ENVIRONMENT` | `development` or `production` | ✅ |
| `SESSION_SECRET_KEY` | 64-char hex secret used to sign session tokens | ✅ |
| `SESSION_TTL_SECONDS` | Session lifetime in seconds (default `7200`) | Optional |
| `ENABLE_DEMO_ACCOUNTS` | Enables demo login credentials — must be `false` in production | ✅ |
| `ALLOWED_ORIGINS` | Comma-separated list of allowed frontend origins (CORS) | ✅ |
| `VITE_API_BASE` | Backend URL, set at frontend build time | ✅ |

Never commit `.env` files — only `.env.example` templates with dummy values are tracked in Git.

---

## 🛡️ Security

Security isn't an afterthought here — it's core to what RiskLock does. Highlights:

- Passwords hashed with **PBKDF2-HMAC-SHA256**, 600,000 iterations, unique 32-byte CSPRNG salt per user
- Session tokens are **HMAC-signed**, carry expiration + unique IDs, and can be revoked instantly on logout
- **Constant-time comparisons** throughout auth flow to prevent timing-based user enumeration
- **Rate limiting + lockout** on all authentication endpoints
- **Content-Security-Policy** and **HSTS** enforced on every response
- Audit logs are automatically scrubbed of credentials, tokens, and secrets before being written

Found a security issue? Please report it privately rather than opening a public issue. *(Security mail - gawasaastha12@gmail.com)*

---

## ☁️ Deployment

RiskLock is designed to deploy cleanly to [Render](https://render.com) as two services:

1. **Backend** — Web Service running `uvicorn main:app`
2. **Frontend** — Static Site serving the Vite production build

See `render.yaml` for the full Blueprint configuration, and set the environment variables listed above in the Render dashboard before your first deploy.

> ⚠️ **Persistence note:** Render's default filesystem is ephemeral. If you're storing users and audit logs as local JSON/JSONL files, they will be wiped on every redeploy or restart. For anything beyond a demo, migrate `registered_users.json` and `audit_log.jsonl` to a persistent disk or a managed database (e.g., Render PostgreSQL).

---

## 🧪 Testing

```bash
# Backend security & functional test suite
python test_security.py

# Frontend production build check
cd frontend_v2 && npm run build
```

---

📄 License

This is a personal project, built and maintained solo. All rights reserved unless otherwise stated — feel free to reach out if you'd like to use or reference any part of it.

👤 About

RiskLock is an independent project designed and built from the ground up, covering everything from the risk-assessment logic to the security architecture and deployment pipeline.
