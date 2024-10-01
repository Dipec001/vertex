web: gunicorn vertex.wsgi:application
worker: celery -A vertex.celery worker --pool=solo -l info