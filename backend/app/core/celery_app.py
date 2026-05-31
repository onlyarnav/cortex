from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "cortex",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.document_worker"]
    )

celery_app.conf.task_track_started = True
celery_app.conf.worker_pool = "solo"