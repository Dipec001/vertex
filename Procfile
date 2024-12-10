web: daphne vertex.asgi:application --port $PORT --bind 0.0.0.0 -v2
worker: celery -A vertex worker -l INFO --pool=solo --queues=priority_high,default --concurrency=4 --events
beat: celery -A vertex beat -l info