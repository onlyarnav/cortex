from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "cortex",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.document_worker"],
)

celery_app.conf.update(
    task_track_started=True,
    worker_pool="solo",  # required on Windows
    task_acks_late=True,
    worker_max_tasks_per_child=50,
    result_expires=3600,
)