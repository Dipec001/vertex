web: daphne vertex.asgi:application --port $PORT --bind 0.0.0.0 -v2
worker: celery -A vertex worker -l INFO --queues=default --events
priority_worker: celery -A vertex worker -l INFO --queues=priority_high --events
beat: celery -A vertex beat -l info
