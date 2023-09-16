import os
import ssl

from flask import Flask
from celery import Celery
from celery import Task

from dotenv import load_dotenv


def create_app(test_config=None):
    load_dotenv()
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        UPLOAD_FOLDER=os.path.join(app.instance_path, 'uploads'),
        DATABASE=os.path.join(app.instance_path, 'gptr.sqlite'),
        CELERY=dict(
            broker_url=os.environ.get('REDIS_URL'),
            result_backend=os.environ.get('REDIS_URL'),
            task_ignore_result=True,
            broker_use_ssl={
                'ssl_cert_reqs': ssl.CERT_REQUIRED
            },
            redis_backend_use_ssl = {
                'ssl_cert_reqs': ssl.CERT_REQUIRED
            }

        ),
    )
    
    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    try:
        os.makedirs(app.instance_path)
    except:
        pass

    # uploads folder should exist
    try:
        os.makedirs(os.path.join(app.instance_path, 'uploads'))
    except:
        pass

    celery_init_app(app)


    @app.route('/hello')
    def hello():
        return 'hello'
    
    from . import db
    db.init_app(app)


    from . import prompt
    app.register_blueprint(prompt.bp)
    app.add_url_rule('/', endpoint='index')

    return app


def celery_init_app(app: Flask) -> Celery:
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config["CELERY"])
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    return celery_app