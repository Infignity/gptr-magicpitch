import os

from flask import Flask


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        UPLOAD_FOLDER=os.path.join(app.instance_path, 'uploads'),
        DATABASE=os.path.join(app.instance_path, 'gptr.sqlite')
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

    @app.route('/hello')
    def hello():
        return 'Hello'
    
    from . import db
    db.init_app(app)


    from . import prompt
    app.register_blueprint(prompt.bp)
    app.add_url_rule('/', endpoint='index')
    


    return app