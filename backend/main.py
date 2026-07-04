from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

import models
import schemas
from database import engine, get_db, Base
from monitor import check_all_urls

Base.metadata.create_all(bind=engine)

scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run one check immediately on boot so the dashboard isn't empty,
    # then every 60 seconds after that.
    check_all_urls()
    scheduler.add_job(check_all_urls, "interval", seconds=60, id="ping_job")
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Uptime Monitor API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "service": "uptime-monitor-backend"}


@app.post("/api/urls", response_model=schemas.URLOut, status_code=201)
def add_url(payload: schemas.URLCreate, db: Session = Depends(get_db)):
    existing = db.query(models.MonitoredURL).filter(
        models.MonitoredURL.url == payload.url
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="This URL is already being monitored.")

    entry = models.MonitoredURL(name=payload.name, url=payload.url)
    db.add(entry)
    db.commit()
    db.refresh(entry)

    # Kick off an immediate check so the new row doesn't sit empty
    # for up to 60 seconds waiting on the scheduler.
    from monitor import ping_url
    status_code, response_time_ms, is_up, error_message = ping_url(entry.url)
    check = models.HealthCheck(
        url_id=entry.id,
        status_code=status_code,
        response_time_ms=response_time_ms,
        is_up=is_up,
        error_message=error_message,
    )
    db.add(check)
    db.commit()
    db.refresh(entry)

    return _serialize_url(entry, db)


@app.get("/api/urls", response_model=List[schemas.URLOut])
def list_urls(db: Session = Depends(get_db)):
    entries = db.query(models.MonitoredURL).order_by(models.MonitoredURL.created_at).all()
    return [_serialize_url(e, db) for e in entries]


@app.delete("/api/urls/{url_id}", status_code=204)
def delete_url(url_id: int, db: Session = Depends(get_db)):
    entry = db.query(models.MonitoredURL).filter(models.MonitoredURL.id == url_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="URL not found")
    db.delete(entry)
    db.commit()
    return


@app.get("/api/urls/{url_id}/history", response_model=List[schemas.CheckOut])
def url_history(url_id: int, limit: int = 20, db: Session = Depends(get_db)):
    entry = db.query(models.MonitoredURL).filter(models.MonitoredURL.id == url_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="URL not found")
    checks = (
        db.query(models.HealthCheck)
        .filter(models.HealthCheck.url_id == url_id)
        .order_by(models.HealthCheck.checked_at.desc())
        .limit(limit)
        .all()
    )
    return checks


def _serialize_url(entry: models.MonitoredURL, db: Session) -> schemas.URLOut:
    latest = (
        db.query(models.HealthCheck)
        .filter(models.HealthCheck.url_id == entry.id)
        .order_by(models.HealthCheck.checked_at.desc())
        .first()
    )
    return schemas.URLOut(
        id=entry.id,
        name=entry.name,
        url=entry.url,
        created_at=entry.created_at,
        latest_check=latest,
    )
