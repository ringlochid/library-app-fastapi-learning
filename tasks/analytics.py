"""Analytics/statistics tasks."""
from celery import shared_task


@shared_task
def compute_stats() -> dict:
    """
    Placeholder analytics task. Compute aggregates and store results.
    """
    # TODO: implement real analytics
    return {"status": "ok"}
