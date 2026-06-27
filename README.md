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

## Run with PostgreSQL

```bash
docker compose up --build -d
```

The API listens on:

```text
http://127.0.0.1:8020
```

PostgreSQL runs as the `identity-db` service. User data is persisted in the
Docker volume named `identity-db-data`.

Default local database settings are in `.env`. Change the password before using
this outside a local lab environment.

### Access the database

The PostgreSQL container is named `cantelcox-identity-db`. Open a `psql` shell
inside the database container with:

```bash
docker exec -it cantelcox-identity-db psql -U identity -d identity_db
```

Useful `psql` commands:

```text
\dt
\d users
SELECT * FROM users;
\q
```

From another container in the same Docker Compose network, use:

```text
postgresql://identity:identity_password@identity-db:5432/identity_db
```

The database port is not exposed on the host by default. To connect with a local
desktop client, add a port mapping to the `identity-db` service:

```yaml
ports:
  - "5432:5432"
```

Then connect to `127.0.0.1:5432` with database `identity_db`, user `identity`,
and password `identity_password`.

## Endpoints MVP

```text
GET    /health
POST   /v1/auth/accounts
POST   /v1/auth/login
POST   /v1/auth/mfa/request
POST   /v1/auth/mfa/verify
POST   /v1/auth/token
GET    /v1/auth/me
POST   /v1/auth/logout
POST   /v1/users
GET    /v1/users
GET    /v1/users/{user_id}
PATCH  /v1/users/{user_id}/status
```

### Authentication with MFA

`POST /v1/auth/login` validates the email and password, then creates a simulated
MFA challenge instead of returning an access token immediately.

Create accounts with:

```json
{
  "full_name": "Jane Client",
  "phone_number": "+1 514 555 0101",
  "email": "jane@example.com",
  "password": "password123"
}
```

The API also accepts `fullName`, `phoneNumber`, or `phone` aliases from the
frontend.

Example response:

```json
{
  "mfa_required": true,
  "challenge_id": "challenge-token",
  "user_id": "user-id",
  "login_token": "temporary-login-token",
  "token_login": "temporary-login-token",
  "expires_at": "2026-06-20T20:30:00Z",
  "channel": "simulated",
  "remaining_attempts": 3,
  "debug_otp": "123456"
}
```

`debug_otp` is enabled by default for local lab testing. Set
`MFA_DEBUG_OTP=false` to hide it when another delivery channel is configured.

The frontend can request a delivery channel with the temporary login token:

```http
POST /v1/auth/mfa/request
Authorization: Bearer temporary-login-token
Content-Type: application/json

{
  "user_id": "user-id",
  "channel": "sms",
  "destination": "+1 514 555 0101"
}
```

For email:

```json
{
  "user_id": "user-id",
  "channel": "email",
  "destination": "jane@example.com"
}
```

Then verify the returned challenge code:

```http
POST /v1/auth/mfa/verify
Content-Type: application/json

{
  "challenge_id": "challenge-token",
  "code": "123456"
}
```

Successful verification returns the bearer access token and user profile.
Invalid codes return `401`; after three failed attempts the challenge is blocked
with `403`.

## CI/CD deployment

The repository includes a GitHub Actions workflow at `.github/workflows/deploy.yml`.
It deploys on every push to `main` using a self-hosted Linux runner installed on
the VM.

On the VM:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose
sudo systemctl enable --now docker
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

Verify Docker works for the runner user without `sudo`:

```bash
docker ps
docker compose version || docker-compose --version
```

If this VM is an LXC container, Docker requires nesting to be enabled on the
host before Docker can run reliably inside it.

### Run the VM with LXC

On the LXC host, enable nesting for the container that runs this service.
Replace `<CONTAINER_NAME>` with the LXC container name:

```bash
lxc stop <CONTAINER_NAME>
lxc config set <CONTAINER_NAME> security.nesting true
lxc config set <CONTAINER_NAME> security.privileged true
lxc start <CONTAINER_NAME>
```

Open a shell inside the LXC container:

```bash
lxc exec <CONTAINER_NAME> -- bash
```

Then go to the project directory and start the service:

```bash
cd /path/to/LOG430-cantelcox-identity-service
docker compose up --build -d
```

Verify that the containers are running:

```bash
docker ps
```

The API should be available on:

```text
http://<LXC_IP>:8020
```

Then add a GitHub self-hosted runner from:

```text
Repository -> Settings -> Actions -> Runners -> New self-hosted runner
```

Install it on the VM and run it as a service. The runner user must be able to run:

```bash
scripts/deploy-compose.sh deploy
```

After that, pushing to `main` will rebuild and restart the service on the VM.
