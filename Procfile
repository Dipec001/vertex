web: daphne vertex.asgi:application --port $PORT --bind 0.0.0.0 -v2
worker: celery -A vertex worker -l INFO --queues=default --concurrency=4 --events
priority_worker: celery -A vertex worker -l INFO --queues=priority_high --concurrency=4 --events
beat: celery -A vertex beat -l info
