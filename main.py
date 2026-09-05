from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Literal, Dict, Any, Optional
import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
import json
import os
import time
import secrets
import hmac
import hashlib
import base64
from collections import defaultdict
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

ENVIRONMENT = os.environ.get("ENVIRONMENT", "development").lower()
ENABLE_DEMO_ACCOUNTS = os.environ.get("ENABLE_DEMO_ACCOUNTS", "false" if ENVIRONMENT == "production" else "true").lower() in ("true", "1", "yes")
DEMO_ADMIN_USER = os.environ.get("DEMO_ADMIN_USER", "admin")
DEMO_ADMIN_PASSWORD = os.environ.get("DEMO_ADMIN_PASSWORD", "risklock")

# In production, require explicit SESSION_SECRET_KEY without silent fallback
_session_secret = os.environ.get("SESSION_SECRET_KEY")
if not _session_secret:
    if ENVIRONMENT == "production":
        raise RuntimeError("CRITICAL DEPLOYMENT CONFIGURATION ERROR: SESSION_SECRET_KEY must be explicitly set via environment variables in production!")
    _session_secret = "dev_ephemeral_key_" + secrets.token_hex(32)
SESSION_SECRET_KEY = _session_secret.encode("utf-8")

SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL_SECONDS", "7200"))  # 2 hours default

# Initialize FastAPI app with production security configuration
app = FastAPI(
    title="RiskLock Fraud Decision Engine API",
    description="Real-time 3-Tier Expected-Cost Fraud Detection & Explanation API (Track 02 · AI Risk Manager)",
    version="1.0.0",
    docs_url=None if ENVIRONMENT == "production" else "/docs",
    redoc_url=None if ENVIRONMENT == "production" else "/redoc",
    debug=False
)

# 1. CORS Lockdown
allowed_origins_env = os.environ.get("ALLOWED_ORIGINS", "")
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
if not allowed_origins:
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:3002",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3002",
        "http://127.0.0.1:5173",
    ]
frontend_url = os.environ.get("FRONTEND_URL")
if frontend_url and frontend_url not in allowed_origins:
    allowed_origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https:\/\/.*\.onrender\.com$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# 2. HTTP Security Headers, CSP, HSTS & Body Size Limit Middleware (Max 1MB)
@app.middleware("http")
async def add_security_headers_and_limit(request: Request, call_next):
    # Enforce request size limit to prevent memory exhaustion / DoS
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 1_048_576:
        return JSONResponse(
            status_code=413,
            content={"detail": "Payload too large. Maximum allowed size is 1MB."}
        )
    
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: https: blob:; "
        "connect-src 'self' http://localhost:* ws://localhost:* https://*.onrender.com; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
    return response

# 3. Global Exception Handler (Never leak server stack traces to users)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"[SECURITY ALERT] {request.method} {request.url.path} - Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal processing error occurred. Incident has been logged securely."}
    )

# 4. Rate Limiting & Account Lockout
RATE_LIMIT_ASSESS = 60
AUTH_RATE_LIMIT_PER_MINUTE = 5
LOCKOUT_THRESHOLD = 5
LOCKOUT_DURATION_SECONDS = 900  # 15 minutes

_assess_request_history: Dict[str, List[float]] = defaultdict(list)
_auth_request_history: Dict[str, List[float]] = defaultdict(list)
_auth_failed_attempts: Dict[str, List[float]] = defaultdict(list)
_auth_locked_entities: Dict[str, float] = {}

def check_rate_limit(client_ip: str) -> None:
    now = time.time()
    cutoff = now - 60.0
    history = [t for t in _assess_request_history[client_ip] if t > cutoff]
    if len(history) >= RATE_LIMIT_ASSESS:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded ({RATE_LIMIT_ASSESS} requests/minute). Please slow down."
        )
    history.append(now)
    _assess_request_history[client_ip] = history

def check_auth_security(client_ip: str, username: str) -> None:
    now = time.time()
    
    # Check if IP or username is locked out
    for entity in (client_ip, username.lower()):
        locked_until = _auth_locked_entities.get(entity, 0.0)
        if now < locked_until:
            remaining = int(locked_until - now)
            raise HTTPException(
                status_code=429,
                detail=f"Access temporarily locked due to excessive authentication failures. Retry in {remaining} seconds."
            )
            
    # Sliding window rate limit (5 attempts/min per IP)
    cutoff = now - 60.0
    history = [t for t in _auth_request_history[client_ip] if t > cutoff]
    if len(history) >= AUTH_RATE_LIMIT_PER_MINUTE:
        raise HTTPException(
            status_code=429,
            detail="Too many authentication attempts. Maximum 5 attempts per minute allowed."
        )
    history.append(now)
    _auth_request_history[client_ip] = history

def record_failed_auth(client_ip: str, username: str) -> None:
    now = time.time()
    cutoff = now - LOCKOUT_DURATION_SECONDS
    for entity in (client_ip, username.lower()):
        attempts = [t for t in _auth_failed_attempts[entity] if t > cutoff]
        attempts.append(now)
        _auth_failed_attempts[entity] = attempts
        if len(attempts) >= LOCKOUT_THRESHOLD:
            _auth_locked_entities[entity] = now + LOCKOUT_DURATION_SECONDS

def record_successful_auth(client_ip: str, username: str) -> None:
    _auth_failed_attempts.pop(client_ip, None)
    _auth_failed_attempts.pop(username.lower(), None)
    _auth_locked_entities.pop(client_ip, None)
    _auth_locked_entities.pop(username.lower(), None)

# 3. Dedicated audit log directory (never exposed via static files)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
AUDIT_LOG_PATH = os.path.join(LOGS_DIR, "audit_log.jsonl")

# Paths to model & calibrator artifacts
MODEL_PATH = os.path.join(BASE_DIR, "models", "baseline_xgboost.json")
CALIBRATOR_PATH = os.path.join(BASE_DIR, "models", "calibrated_platt_scaler.joblib")

# Feature column order matching exact model training vector
FEATURE_COLS = [
    'amount', 'oldbalanceOrg', 'newbalanceOrig', 'oldbalanceDest', 'newbalanceDest',
    'type_CASH_IN', 'type_CASH_OUT', 'type_DEBIT', 'type_PAYMENT', 'type_TRANSFER'
]

# Load artifacts directly on module import
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Model file not found at: {MODEL_PATH}")
if not os.path.exists(CALIBRATOR_PATH):
    raise FileNotFoundError(f"Calibrator file not found at: {CALIBRATOR_PATH}")

model = xgb.XGBClassifier()
model.load_model(MODEL_PATH)
calibrator = joblib.load(CALIBRATOR_PATH)
print("RiskLock Engine initialized: Baseline XGBoost and Platt Calibrator loaded successfully.")

# Input Request Schema with strict bounds & validation
class TransactionRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Transaction amount in INR (must be positive)", example=98086.09)
    oldbalanceOrg: float = Field(..., ge=0, description="Sender balance before transaction", example=98086.09)
    newbalanceOrig: float = Field(..., ge=0, description="Sender balance after transaction", example=0.0)
    oldbalanceDest: float = Field(..., ge=0, description="Recipient balance before transaction", example=0.0)
    newbalanceDest: float = Field(..., ge=0, description="Recipient balance after transaction", example=0.0)
    type: Literal["CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"] = Field(..., description="Transaction type", example="TRANSFER")

# Feature Contribution Item Schema
class FeatureContribution(BaseModel):
    name: str
    value: float
    shap: float

# Response Schema
class DecisionResponse(BaseModel):
    risk_score: float
    tier: Literal["APPROVE", "STEP_UP", "BLOCK"]
    segment: str
    reason: str
    top_features: List[FeatureContribution]
    timestamp: str

def generate_reason_code(txn_data: dict, top_features: List[Dict[str, Any]], tier: str) -> str:
    amount = txn_data['amount']
    old_org = txn_data['oldbalanceOrg']
    new_org = txn_data['newbalanceOrig']
    txn_type = txn_data['type']
    
    reasons = []
    
    if tier == "APPROVE":
        # Reassuring / Protective Reasons for Approved Transactions
        for feat in top_features:
            f_name = feat['name']
            f_val = feat['value']
            s_val = feat['shap']
            
            if s_val < 0:
                if f_name == 'oldbalanceOrg':
                    reasons.append("Sender account balance profile lowers risk")
                elif f_name == 'newbalanceOrig':
                    reasons.append("Account balance retained after transaction")
                elif f_name == 'amount':
                    reasons.append(f"Transaction amount INR {amount:,.0f} aligns with safe baseline range")
                elif f_name in ['type_PAYMENT', 'type_CASH_IN', 'type_DEBIT']:
                    reasons.append(f"Low-risk transaction channel ({txn_type})")
                elif f_name in ['type_TRANSFER', 'type_CASH_OUT']:
                    reasons.append(f"Channel activity ({txn_type}) consistent with safe user behavior")
                elif f_name in ['oldbalanceDest', 'newbalanceDest']:
                    reasons.append("Recipient account balance history aligns with normal activity")
                    
        if not reasons:
            reasons.append(f"Transaction behavior aligns with low-risk baseline profile ({txn_type} channel)")
            
    else:  # STEP_UP or BLOCK
        # Risk Explanation Reasons for Flagged Transactions
        if abs(amount - old_org) < 0.01 and old_org > 0 and new_org == 0:
            reasons.append("Full account balance transferred out (100% drain pattern)")
            
        for feat in top_features:
            f_name = feat['name']
            f_val = feat['value']
            s_val = feat['shap']
            
            if s_val > 0:  # Feature pushes fraud risk
                if f_name == 'newbalanceOrig' and new_org == 0 and old_org > 0 and "100% drain pattern" not in "".join(reasons):
                    reasons.append("Sender origin account balance drained to 0")
                elif f_name == 'amount' and amount > 500000:
                    reasons.append(f"High-value transfer amount (INR {amount:,.0f})")
                elif f_name == 'amount':
                    reasons.append(f"Transaction amount INR {amount:,.0f} relative to expected profile")
                elif f_name in ['type_TRANSFER', 'type_CASH_OUT'] and txn_type in ['TRANSFER', 'CASH_OUT']:
                    reasons.append(f"High-risk transaction channel ({txn_type})")
                elif f_name == 'oldbalanceOrg' and old_org > 0:
                    reasons.append(f"Origin balance (INR {old_org:,.0f}) matches transfer pattern")
                elif f_name in ['newbalanceDest', 'oldbalanceDest']:
                    reasons.append("Recipient destination balance anomaly")
            elif s_val < 0:  # Protective feature context in flagged txn
                if f_name == 'oldbalanceOrg':
                    reasons.append(f"Sender balance (INR {old_org:,.0f}) provides partial risk mitigation")
                elif f_name == 'amount':
                    reasons.append(f"Moderate amount (INR {amount:,.0f}) lowers risk severity")
                    
        if not reasons:
            reasons.append(f"Elevated fraud risk in {txn_type} channel for INR {amount:,.0f}")
            
    return " | ".join(reasons[:2])

@app.get("/")
def root_info():
    return {
        "service": "RiskLock Fraud Decision Engine API",
        "version": "1.0.0",
        "status": "online",
        "health": "/health"
    }

@app.get("/health")
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "environment": ENVIRONMENT,
        "demo_accounts_enabled": ENABLE_DEMO_ACCOUNTS,
        "model_loaded": model is not None and calibrator is not None,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.post("/assess", response_model=DecisionResponse)
def assess_transaction(txn: TransactionRequest, request: Request):
    client_ip = request.client.host if request.client else "127.0.0.1"
    check_rate_limit(client_ip)

    if model is None or calibrator is None:
        raise HTTPException(status_code=500, detail="Models not properly initialized.")
        
    txn_dict = txn.model_dump() if hasattr(txn, 'model_dump') else txn.dict()
    
    # 1. Build one-hot encoded feature vector
    input_vector = {col: 0.0 for col in FEATURE_COLS}
    input_vector['amount'] = float(txn.amount)
    input_vector['oldbalanceOrg'] = float(txn.oldbalanceOrg)
    input_vector['newbalanceOrig'] = float(txn.newbalanceOrig)
    input_vector['oldbalanceDest'] = float(txn.oldbalanceDest)
    input_vector['newbalanceDest'] = float(txn.newbalanceDest)
    
    type_col = f"type_{txn.type}"
    if type_col in input_vector:
        input_vector[type_col] = 1.0
        
    X_input = pd.DataFrame([input_vector], columns=FEATURE_COLS)
    
    # 2. Predict raw probability & calibrate via Platt Scaler
    p_raw = float(model.predict_proba(X_input)[0, 1])
    p_cal = float(calibrator.predict_proba(np.array([[p_raw]]))[0, 1])
    
    # 3. Determine balance segment & select Pareto-adjusted threshold
    old_org = txn.oldbalanceOrg
    if old_org == 0:
        segment = "1. Zero Balance (INR 0)"
        threshold = 33.333333
    elif 0 < old_org <= 50000:
        segment = "2. Low Balance (INR 1 - 50k)"
        threshold = 33.333333
    elif 50000 < old_org <= 250000:
        segment = "3. Mid Balance (INR 50k - 250k)"
        threshold = 13417.98  # Pareto-adjusted threshold (INR 13,417.98)
    else:
        segment = "4. High Balance (> INR 250k)"
        threshold = 33.333333
        
    # 4. Apply 3-Tier expected-cost decision rule
    risk_product = p_cal * txn.amount
    if risk_product > 4700.0:
        tier = "BLOCK"
    elif risk_product > threshold:
        tier = "STEP_UP"
    else:
        tier = "APPROVE"
        
    # 5. Compute top-3 SHAP feature attributions
    dmat = xgb.DMatrix(X_input)
    shap_vals = model.get_booster().predict(dmat, pred_contribs=True)[0, :-1]
    
    top_indices = np.argsort(np.abs(shap_vals))[::-1][:3]
    
    top_features_list = []
    for idx in top_indices:
        f_name = FEATURE_COLS[idx]
        f_val = float(X_input.iloc[0, idx])
        s_val = float(shap_vals[idx])
        top_features_list.append({"name": f_name, "value": f_val, "shap": s_val})
        
    reason = generate_reason_code(txn_dict, top_features_list, tier)
    utc_now = datetime.now(timezone.utc).isoformat()
    
    top_features_objs = [FeatureContribution(**f) for f in top_features_list]
    
    response_payload = {
        "risk_score": round(p_cal, 6),
        "tier": tier,
        "segment": segment,
        "reason": reason,
        "top_features": [f.model_dump() if hasattr(f, 'model_dump') else f.dict() for f in top_features_objs],
        "timestamp": utc_now
    }
    
    # 6. Audit Trail Logging (Append-only to audit_log.jsonl with redaction hygiene)
    def _sanitize_log_data(d: Any) -> Any:
        sensitive = {"password", "passcode", "token", "secret", "authorization", "auth", "key", "cookie"}
        if isinstance(d, dict):
            sanitized = {}
            for k, v in d.items():
                if str(k).lower() in sensitive:
                    sanitized[k] = "[REDACTED]"
                else:
                    sanitized[k] = _sanitize_log_data(v)
            return sanitized
        elif isinstance(d, list):
            return [_sanitize_log_data(item) for item in d]
        return d

    audit_entry = _sanitize_log_data({
        "timestamp": utc_now,
        "input": txn_dict,
        "output": response_payload
    })
    
    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(audit_entry) + "\n")
        
    return DecisionResponse(**response_payload)


# Auth Schemas & Ingress Endpoints with Hardened Security
class AuthRequest(BaseModel):
    username: str = Field(
        ...,
        min_length=3,
        max_length=32,
        pattern=r"^[a-zA-Z0-9_.-]+$",
        description="Alphanumeric operator identifier"
    )
    password: str = Field(..., min_length=6, max_length=128, description="Passcode (min 6 characters)")

USERS_FILE = os.path.join(LOGS_DIR, "registered_users.json")

# Cryptographically Secure PBKDF2 Password Hashing (600,000 iterations + 32-byte CSPRNG salt)
def hash_password(password: str, salt_hex: Optional[str] = None) -> tuple[str, str]:
    if not salt_hex:
        salt_hex = secrets.token_hex(32)
    salt_bytes = bytes.fromhex(salt_hex)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        iterations=600_000
    )
    return key.hex(), salt_hex

def verify_password(password: str, stored_hash: str, salt_hex: str) -> bool:
    salt_bytes = bytes.fromhex(salt_hex)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        iterations=600_000
    )
    return secrets.compare_digest(key.hex(), stored_hash)

# Session Management with Expiration & HMAC Signature
_revoked_tokens: set[str] = set()

def create_session_token(username: str) -> tuple[str, int]:
    now = int(time.time())
    exp = now + SESSION_TTL_SECONDS
    jti = secrets.token_hex(16)
    payload_obj = {"sub": username, "iat": now, "exp": exp, "jti": jti}
    payload_bytes = json.dumps(payload_obj, separators=(",", ":")).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode("utf-8").rstrip("=")
    
    signature = hmac.new(SESSION_SECRET_KEY, payload_b64.encode("utf-8"), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
    token = f"{payload_b64}.{sig_b64}"
    return token, exp

def verify_session_token(token: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, sig_b64 = parts
        
        expected_sig = hmac.new(SESSION_SECRET_KEY, payload_b64.encode("utf-8"), hashlib.sha256).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode("utf-8").rstrip("=")
        if not secrets.compare_digest(sig_b64, expected_sig_b64):
            return None
            
        rem = len(payload_b64) % 4
        padded = payload_b64 + ("=" * (4 - rem) if rem else "")
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8"))
        
        if payload.get("jti") in _revoked_tokens:
            return None
            
        if int(time.time()) > payload.get("exp", 0):
            return None
            
        return payload
    except Exception:
        return None

def _get_registered_users() -> Dict[str, Dict[str, Any]]:
    users = {}
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if isinstance(saved, dict):
                    users = saved
        except Exception as e:
            print(f"Warning: Could not read users file: {e}")
    return users

def _save_registered_user(username: str, password_hash: str, salt_hex: str) -> None:
    users = _get_registered_users()
    users[username] = {
        "hash": password_hash,
        "salt": salt_hex,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)

@app.post("/api/auth/login")
@app.post("/auth/login")
def auth_login(auth: AuthRequest, request: Request, response: Response):
    client_ip = request.client.host if request.client else "127.0.0.1"
    u = auth.username.strip().lower()
    p = auth.password.strip()

    # Rate limiting & brute-force lockout protection
    check_auth_security(client_ip, u)

    authenticated_user = None

    # Check environment-gated demo credentials
    if ENABLE_DEMO_ACCOUNTS and DEMO_ADMIN_USER.lower() == u:
        if secrets.compare_digest(DEMO_ADMIN_PASSWORD, p):
            authenticated_user = DEMO_ADMIN_USER

    # Check registered users with PBKDF2 salted hash
    if not authenticated_user:
        users = _get_registered_users()
        for registered_u, creds in users.items():
            if registered_u.lower() == u:
                stored_hash = creds.get("hash", "")
                salt_hex = creds.get("salt", "")
                if stored_hash and salt_hex and verify_password(p, stored_hash, salt_hex):
                    authenticated_user = registered_u
                break

    if not authenticated_user:
        # Dummy verification calculation to prevent timing side-channels
        dummy_salt = "0" * 64
        dummy_hash = "0" * 64
        verify_password(p, dummy_hash, dummy_salt)
        
        record_failed_auth(client_ip, u)
        raise HTTPException(
            status_code=401,
            detail="Invalid identifier or passcode. Repeated failures will trigger a 15-minute lockout."
        )

    # Success: clear failure counters & issue signed token with expiration
    record_successful_auth(client_ip, u)
    token, expires_at = create_session_token(authenticated_user)

    # Set secure HttpOnly, SameSite=Strict cookie
    is_secure = request.url.scheme == "https" or ENVIRONMENT == "production"
    response.set_cookie(
        key="risklock_session",
        value=token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=is_secure,
        samesite="strict",
        path="/"
    )

    return {
        "status": "success",
        "username": authenticated_user,
        "token": token,
        "expires_in": SESSION_TTL_SECONDS,
        "issued_at": datetime.now(timezone.utc).isoformat()
    }

@app.post("/api/auth/register")
@app.post("/auth/register")
def auth_register(auth: AuthRequest, request: Request):
    client_ip = request.client.host if request.client else "127.0.0.1"
    u = auth.username.strip()
    p = auth.password.strip()

    check_auth_security(client_ip, u)

    if ENABLE_DEMO_ACCOUNTS and u.lower() == DEMO_ADMIN_USER.lower():
        raise HTTPException(status_code=409, detail="Identifier is reserved by system policy")

    users = _get_registered_users()
    if any(registered_u.lower() == u.lower() for registered_u in users):
        raise HTTPException(status_code=409, detail="Identifier already registered in access registry")

    pwd_hash, salt = hash_password(p)
    _save_registered_user(u, pwd_hash, salt)

    return {
        "status": "success",
        "username": u,
        "detail": "Operator identity enrolled with PBKDF2-SHA256 salted credentials"
    }

@app.post("/api/auth/logout")
@app.post("/auth/logout")
def auth_logout(request: Request, response: Response):
    auth_header = request.headers.get("Authorization", "")
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    if not token:
        token = request.cookies.get("risklock_session", "")
    if token:
        parsed = verify_session_token(token)
        if parsed and "jti" in parsed:
            _revoked_tokens.add(parsed["jti"])

    response.delete_cookie(key="risklock_session", path="/", samesite="strict")
    return {"status": "success", "detail": "Session invalidated and cookie cleared"}

@app.get("/api/auth/me")
@app.get("/auth/me")
def auth_me(request: Request):
    auth_header = request.headers.get("Authorization", "")
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    if not token:
        token = request.cookies.get("risklock_session", "")
        
    if not token:
        raise HTTPException(status_code=401, detail="No active session token found")
        
    payload = verify_session_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Session expired or invalid. Please re-authenticate.")
        
    return {
        "status": "authenticated",
        "username": payload.get("sub"),
        "expires_at": payload.get("exp")
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    # Production ASGI runner binding to 0.0.0.0
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)


