
gunicorn -w 4 -b 0.0.0.0 'gptr:create_app()' & celery -A make_celery worker --loglevel INFO