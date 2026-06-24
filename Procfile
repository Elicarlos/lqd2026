web: gunicorn liquida2018.wsgi --log-file -
worker: celery -A liquida2018 worker --loglevel=info
beat: celery -A liquida2018 beat --loglevel=info
