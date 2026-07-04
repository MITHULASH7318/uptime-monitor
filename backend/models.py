from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class MonitoredURL(Base):
    __tablename__ = "monitored_urls"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    checks = relationship(
        "HealthCheck", back_populates="url_entry", cascade="all, delete-orphan"
    )


class HealthCheck(Base):
    __tablename__ = "health_checks"

    id = Column(Integer, primary_key=True, index=True)
    url_id = Column(Integer, ForeignKey("monitored_urls.id"))
    status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Float, nullable=True)
    is_up = Column(Boolean, default=False)
    error_message = Column(String, nullable=True)
    checked_at = Column(DateTime(timezone=True), server_default=func.now())

    url_entry = relationship("MonitoredURL", back_populates="checks")
