import os
import sys
from celery import Celery
from flask import Flask, request
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager
from flask.ext.cors import CORS
from werkzeug.local import LocalProxy

# Setup logging config
from setup_logging import setup_logging
setup_logging()

# Initialize after setting logging config
import logging
logger = logging.getLogger(__name__)

# Initialize app-based objects
db = SQLAlchemy()
login_manager = LoginManager()
cors = CORS()

def create_app(**kwargs):
    '''
    Initialize Flask application
    '''
    app = Flask(__name__)
    app.config.from_object('config.DevelopmentConfig')

    db.init_app(app)
    login_manager.init_app(app)

    cors.init_app(app,
        resources=r'/*',
        supports_credentials=True,
        allow_headers='Content-Type'
    )

    ensure_directories(app)
    return app


def create_celery(app):
    '''
    Initialize celery instance given an app
    '''
    celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    return celery


def create_api(app):
    '''
    Attach API endpoints / resources to app
    '''
    from flask.ext.restful import Api
    api = Api()

    from api import add_resources
    api = add_resources(api)
    api.init_app(app)

    return api


def ensure_directories(app):
    if not os.path.isdir(app.config['UPLOAD_DIR']):
        app.logger.info("Creating Upload directory")
        os.mkdir(app.config['UPLOAD_DIR'])
