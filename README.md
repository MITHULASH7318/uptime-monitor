# Uptime Monitor

A small full-stack app that pings a list of URLs on a schedule and shows which ones are up,
which are down, and how fast they responded.

- **Backend**: FastAPI + SQLite, with APScheduler running a background job every 60 seconds
  that checks every registered URL and logs the result.
- **Frontend**: Streamlit dashboard that polls the backend and auto-refreshes every 15 seconds.
- **Storage**: SQLite file, persisted to disk via a Docker volume so history survives restarts.

## 1-line setup

```bash
docker compose up --build
```

- Backend API: http://localhost:8000
- Frontend dashboard: http://localhost:8501

First run downloads and installs everything inside the containers, so give it a minute or two.
Every run after that is fast since Docker caches the layers.

## Testing up vs. down detection

The whole point of the exercise is proving the monitor tells the difference between a live
site and a dead one. Steps:

1. Open the dashboard at http://localhost:8501
2. In the "Add URL" form, add a healthy site:
   - Name: `Example Site`
   - URL: `https://example.com`
3. Add a broken one:
   - Name: `Broken Site`
   - URL: `https://this-domain-does-not-exist-abc123.com`
4. Each new URL gets checked immediately on creation (you don't have to wait for the
   1-minute scheduler), so within a couple of seconds you should see:
   - `Example Site` → 🟢 Up, status code 200, a response time in ms
   - `Broken Site` → 🔴 Down, no status code, DNS resolution failure
5. To see the periodic re-check working, leave the dashboard open — it auto-refreshes every
   15 seconds and the scheduler re-pings every 60 seconds, so the "Last Checked" timestamp
   will keep moving forward on its own.
6. You can also hit the API directly to see raw history:
   ```bash
   curl http://localhost:8000/api/urls
   curl http://localhost:8000/api/urls/1/history
   ```

## Project structure

```
.
├── backend/            # FastAPI app, SQLite models, scheduler, Dockerfile
├── frontend/            # Streamlit dashboard, Dockerfile
├── docker-compose.yml   # Orchestrates both containers on one network
├── AI_LOG.md            # AI collaboration log
└── README.md
```

## Deployment sketch

For an MVP like this I wouldn't reach for Kubernetes — two small services and a SQLite file
don't need that much. My actual pick for this specific app:

- **Backend** → a small container host with a persistent disk (e.g. Render, Railway, or a
  single AWS Fargate task with an EFS mount for the SQLite file). If this had to scale past a
  few dozen URLs or multiple instances, I'd swap SQLite for a managed Postgres (RDS) so the
  scheduler and API could run on more than one node without fighting over a local file.
- **Frontend** → Streamlit Community Cloud, pointed at the deployed backend URL via an
  environment variable. This is genuinely the fastest way to get a public, shareable link for
  a Streamlit app with zero infra to manage.
- **Scheduler** → for anything beyond MVP scale I'd pull the ping job out of the API process
  entirely and run it as its own worker (e.g. a Fargate scheduled task or a Lambda on a
  CloudWatch Events cron), so a slow API deploy never blocks health checks from firing.

Rough Terraform sketch of the "grown-up" version (illustrative, not applied):

```hcl
resource "aws_ecs_cluster" "uptime_monitor" {
  name = "uptime-monitor"
}

resource "aws_ecs_task_definition" "backend" {
  family                   = "uptime-monitor-backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "512"
  container_definitions    = jsonencode([
    {
      name  = "backend"
      image = "<ecr-repo>/uptime-monitor-backend:latest"
      portMappings = [{ containerPort = 8000 }]
      environment = [
        { name = "DATABASE_URL", value = "postgresql://.../uptime" }
      ]
    }
  ])
}

resource "aws_db_instance" "uptime_db" {
  engine         = "postgres"
  instance_class = "db.t4g.micro"
  allocated_storage = 20
  name           = "uptime"
}
```

The frontend in this scaled-up version would either move to its own Fargate task behind an
ALB, or just stay on Streamlit Community Cloud pointed at the ALB's backend URL — no need to
over-engineer the dashboard just because the backend grew up.

## Live demo

_(Fill this in once you've deployed: Streamlit Community Cloud link for the frontend, and
the backend URL it's pointed at.)_
