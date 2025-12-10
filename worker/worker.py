"""
Worker entrypoint. Run with:
    celery -A celery_app worker -l info
"""
from celery_app import app

if __name__ == "__main__":
    app.worker_main()
