import os
import pandas as pd

from dive.base.db import db_access
from dive.base.data.access import get_data
from dive.worker.core import celery, task_app
from dive.worker.ingestion.upload import save_dataset
from dive.worker.transformation.utilities import get_transformed_file_name

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)


def reduce_dataset(project_id, dataset_id, column_ids_to_keep, new_dataset_name_prefix):
    with task_app.app_context():
        df = get_data(project_id=project_id, dataset_id=dataset_id)
        project = db_access.get_project(project_id)
        original_dataset = db_access.get_dataset(project_id, dataset_id)

    preloaded_project = project.get('preloaded', False)
    if preloaded_project:
        project_dir = os.path.join(task_app.config['PRELOADED_PATH'], project['directory'])
    else:
        project_dir = os.path.join(task_app.config['STORAGE_PATH'], str(project_id))

    original_dataset_title = original_dataset['title']
    fallback_title = original_dataset_title[:20]
    dataset_type = '.tsv'
    new_dataset_title, new_dataset_name, new_dataset_path = \
        get_transformed_file_name(project_dir, new_dataset_name_prefix, fallback_title, original_dataset_title, dataset_type)

    df_reduced = df.iloc[:, column_ids_to_keep]

    return df_reduced, new_dataset_title, new_dataset_name, new_dataset_path
