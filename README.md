# CanTelcoX Identity Service

Microservice responsable des utilisateurs et de l'identite.

## Run local

```bash
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

## CI/CD deployment

The repository includes a GitHub Actions workflow at `.github/workflows/deploy.yml`.
It deploys on every push to `main` using a self-hosted Linux runner installed on
the VM.

On the VM:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
```

Create the runner user. The default username is defined in `.env`:

```bash
set -a
. ./.env
set +a

sudo adduser "$RUNNER_USER"
sudo usermod -aG sudo "$RUNNER_USER"
sudo usermod -aG docker "$RUNNER_USER"
su - "$RUNNER_USER"
```

Then add a GitHub self-hosted runner from:

```text
Repository -> Settings -> Actions -> Runners -> New self-hosted runner
```

Install it on the VM and run it as a service. The runner user must be able to run:

```bash
docker compose up --build -d --remove-orphans
```

After that, pushing to `main` will rebuild and restart the service on the VM.
