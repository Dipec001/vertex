web: daphne vertex.asgi:application --port $PORT --bind 0.0.0.0 -v2
worker: celery -A vertex.celery worker --pool=solo -l info
beat: celery -A vertex beat -l info