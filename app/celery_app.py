"""Celery entrypoint expected by infra/docker-compose.yml.

The Celery app itself lives in app/worker.py; this module re-exports it
so `celery -A app.celery_app worker` and `celery -A app.celery_app beat`
resolve correctly.
"""
from app.worker import celery_app

__all__ = ["celery_app"]
