# CanTelcoX Identity Service

Microservice responsable des utilisateurs et de l'identite.

## Run local

```bash
cd services/identity-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8020 --reload
```

Swagger:

```text
http://127.0.0.1:8020/docs
```

## Endpoints MVP

```text
GET    /health
POST   /v1/auth/accounts
POST   /v1/auth/login
POST   /v1/auth/logout
POST   /v1/users
GET    /v1/users
GET    /v1/users/{user_id}
PATCH  /v1/users/{user_id}/status
```
# LOG430-cantelcox-identity-service
