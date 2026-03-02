# ActionOS Startup Analysis

_Researched: 2026-03-02_

## Why Does It Take So Long to Start?

ActionOS runs on **AWS Lambda**, which has a "cold start" problem: after ~5-15
minutes of inactivity the function is frozen. The next request wakes it from
scratch, running:

1. Python runtime initialization
2. Full dependency import tree (all packages in the 36 MB zip)
3. Module-level `boto3.client()` calls at lines 81–82 of `lambda_handler.py` —
   these run credential resolution + network calls before the handler runs

### Package Size Breakdown (36 MB zip)

| Package           | Compressed Size |
| ----------------- | --------------- |
| `googleapiclient` | 13.7 MB         |
| `botocore`        | 13.5 MB         |
| `cryptography`    | 3.8 MB          |
| `google`          | 1.0 MB          |
| others            | ~4 MB           |

`botocore` shouldn't be in the zip at all — the Lambda runtime already provides
`boto3`/`botocore`. It likely crept in via a transitive dependency. Removing it
saves ~13.5 MB and meaningfully shortens cold start.

---

## All Deployment Options

### Option 1: Keep Lambda — Quick Wins (no migration)

| Fix                                           | Impact                                | Effort               |
| --------------------------------------------- | ------------------------------------- | -------------------- |
| Strip `botocore`/`boto3` from zip             | ~30-40% faster cold start             | Low                  |
| Lazy-init boto3 clients (move inside handler) | Moves network I/O out of import phase | Low                  |
| CloudWatch warmup ping every 5 min            | Eliminates cold starts entirely       | Very low             |
| Provisioned Concurrency                       | Zero cold starts, guaranteed          | Low (costs ~$3-5/mo) |

**Warmup ping**: Add a free EventBridge rule that invokes the Lambda every 5
minutes. At Lambda's free tier (1M requests/mo), this costs $0.

### Option 2: AWS App Runner (~$5-15/mo)

Managed container service. Set min instances = 1 → zero cold starts. Deploy via
container image (Docker) or source code. Good fit if you want to stay in AWS but
hate Lambda cold starts. HTTP-native, no API Gateway needed.

### Option 3: Fly.io (free–$5/mo)

- Deploy a Docker container globally
- `fly scale min 1` → always on, zero cold starts
- Free tier: 3 shared VMs, 256 MB RAM each
- Migration: wrap the handler logic in Flask/FastAPI

### Option 4: Railway ($5/mo hobby)

- Connect GitHub repo → auto-deploy on push
- Always-on containers, no cold starts
- Simplest migration path (Flask/FastAPI wrapper)
- $5/mo includes enough compute for personal tools

### Option 5: Google Cloud Run (pay-per-request)

- Very similar to Lambda but `--min-instances=1` keeps it warm
- Good Python support, Docker-native
- Free tier: 2M requests/mo
- Cold start when min-instances=0 (same problem unless you pay for always-on)

### Option 6: AWS EC2 t4g.nano (~$3/mo)

- Always running, zero cold starts
- Run Flask/FastAPI yourself (gunicorn/uvicorn)
- Most manual: SSH, security patches, process management
- Free tier eligible (t2.micro, 12 months)

---

## Recommendation

**Fastest path with zero cost**: Add a CloudWatch Events warmup ping. One
EventBridge rule, no code changes, eliminates cold starts immediately.

**Best long-term if you want to escape Lambda**: **Railway** — easiest migration
(Flask wrapper around existing handler logic), GitHub-connected auto-deploy,
always-on, $5/mo.

**Best if you want to stay in AWS**: Enable **Provisioned Concurrency** on the
Lambda or switch to **App Runner**. Both eliminate cold starts with minimal
migration work.
