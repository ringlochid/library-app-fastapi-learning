"""
Media-related tasks: validation, resize, virus scan, S3 moves.
Implement real logic as needed; placeholders provided.
"""
from celery import shared_task


@shared_task
def process_upload(key: str) -> str:
    """
    Placeholder: download from S3, validate/scan/resize, write processed key.
    Return the final key written.
    """
    # TODO: implement processing
    return key
