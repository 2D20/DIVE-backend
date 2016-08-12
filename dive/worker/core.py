from celery import Celery
from celery.utils.log import get_task_logger
from dive.base.core import create_app

task_app = create_app()
celery = Celery(task_app.import_name, broker=task_app.config['CELERY_BROKER_URL'])
print task_app.config
celery.conf.update(task_app.config)
