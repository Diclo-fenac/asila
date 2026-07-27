# Runbook: Local Deployment & Stack Validation

This runbook guides Platform Operators through deploying, verifying, and troubleshooting a local or single-node production Aasila stack using Docker Compose and the Typer CLI.

---

## 1. Prerequisites
* **Operating System**: Linux or macOS
* **Container Engine**: Docker Engine 24.0+ with Docker Compose v2+
* **Python Runtime**: Python 3.11+ (for running the CLI or local backend)

---

## 2. Standard Deployment Procedure

### Step 1: Clone & Bootstrap Configuration
Navigate to the repository root and initialize the local environment configuration:
```bash
git clone https://github.com/asila-ai/aasila.git
cd aasila
python3 -m cli.main init
```
*Note: If `.env` is missing, `asila init` will automatically generate it from `.env.example`, populating secure, randomized hex secrets for `ASILA_MASTER_KEY`, `ASILA_SETUP_TOKEN`, and `POSTGRES_PASSWORD`.*

### Step 2: Launch Container Services
Start the underlying infrastructure (PostgreSQL with `pgvector`, Redis, Docling OCR, Ollama, and API backend) in detached mode:
```bash
docker compose up -d
```
Verify container startup status:
```bash
docker compose ps
```

### Step 3: Run Diagnostics & Health Checks
Execute the diagnostic health probe to confirm all internal service dependencies are operational:
```bash
python3 -m cli.main doctor
# Or using the command alias:
python3 -m cli.main status
```
**Expected Output**:
```
Asila System Diagnostics
================================================================================
  ✔ PostgreSQL Database: Connected (latency: ~2ms)
  ✔ Redis Queue Engine: Connected (latency: ~1ms)
  ✔ Ollama Embedding Service: Healthy (latency: ~15ms)
  ✔ Docling Document Converter: Ready (latency: ~8ms)
================================================================================
System Status: HEALTHY
```

---

## 3. Automated Release Verification

Before promoting a deployment or opening pull requests, execute the automated security and release verification gate:
```bash
bash scripts/security_gate.sh
```
This gate automatically validates Python AST syntax, PostgreSQL RLS migration policies, full pytest unit/integration suites, CLI operator interfaces, and MCP protocols.

---

## 4. Troubleshooting & Common Failure Modes

### Failure Mode A: Database Connection Refused / Out of Memory
* **Symptom**: `asila doctor` reports PostgreSQL down or container exits with code 137.
* **Diagnosis**: Check Docker logs for PostgreSQL memory limits or port conflicts on `5432`:
  ```bash
  docker compose logs postgresql
  ```
* **Resolution**: Ensure your host system has at least 4GB of available RAM allocated to Docker. If port 5432 is occupied by a local Postgres instance, modify `docker-compose.yml` port mappings.

### Failure Mode B: Docling OCR Converter Timeout / Circuit Broken
* **Symptom**: `asila doctor` reports Docling down or ingestion jobs fail with circuit breaker errors.
* **Diagnosis**: The Docling container requires significant CPU/RAM during initial model weights download:
  ```bash
  docker compose logs -f docling
  ```
* **Resolution**: Wait 2-3 minutes on initial boot for PyTorch/Docling model initialization. If failures persist, restart the converter service:
  ```bash
  docker compose restart docling
  ```

### Failure Mode C: Setup Token Mismatch
* **Symptom**: `asila init` returns `401 Invalid setup token`.
* **Diagnosis**: The `ASILA_SETUP_TOKEN` exported in your terminal does not match the token in `.env`.
* **Resolution**: Source the `.env` file directly before running CLI commands:
  ```bash
  export $(grep -v '^#' .env | xargs)
  python3 -m cli.main init
  ```
