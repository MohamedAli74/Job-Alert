from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def _utcnow():
    return datetime.now(timezone.utc)


class Job(db.Model):
    __tablename__ = "jobs"

    id          = db.Column(db.Integer, primary_key=True)
    source_name = db.Column(db.String(100), nullable=False)
    title       = db.Column(db.String(300), nullable=False)
    company     = db.Column(db.String(200), nullable=True)
    location    = db.Column(db.String(200), nullable=True)
    url         = db.Column(db.String(1000), unique=True, nullable=False)
    skills      = db.Column(db.Text, nullable=True)        # comma-separated
    role_type   = db.Column(db.String(50), nullable=True)  # inferred from title
    date_found  = db.Column(db.DateTime(timezone=True), default=_utcnow)
    is_notified = db.Column(db.Boolean, default=False, nullable=False)
    is_seen     = db.Column(db.Boolean, default=False, nullable=False)


class Meta(db.Model):
    __tablename__ = "meta"

    id    = db.Column(db.Integer, primary_key=True)
    key   = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(200), nullable=False)
