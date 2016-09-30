import os
import pandas as pd

from dive.base.db import db_access
from dive.base.data.access import get_data
from dive.worker.core import celery, task_app
from dive.worker.ingestion.upload import save_dataset
from dive.worker.transformation.utilities import list_elements_from_indices, get_transformed_file_name

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)


def join_datasets(project_id, left_dataset_id, right_dataset_id, on, left_on, right_on, how, left_suffix, right_suffix, new_dataset_name_prefix):
    with task_app.app_context():
        left_df = get_data(project_id=project_id, dataset_id=left_dataset_id)
        right_df = get_data(project_id=project_id, dataset_id=right_dataset_id)

        project = db_access.get_project(project_id)
        original_left_dataset = db_access.get_dataset(project_id, left_dataset_id)
        original_right_dataset = db_access.get_dataset(project_id, right_dataset_id)

    preloaded_project = project.get('preloaded', False)
    if preloaded_project:
        project_dir = os.path.join(task_app.config['PRELOADED_PATH'], project['directory'])
    else:
        project_dir = os.path.join(task_app.config['STORAGE_PATH'], str(project_id))

    original_left_dataset_title = original_left_dataset['title']
    original_right_dataset_title = original_right_dataset['title']

    fallback_title = original_left_dataset_title[:20] + original_left_dataset_title[:20]
    original_dataset_title = original_left_dataset_title + original_right_dataset_title
    dataset_type = '.tsv'
    new_dataset_title, new_dataset_name, new_dataset_path = \
        get_transformed_file_name(project_dir, new_dataset_name_prefix, fallback_title, original_dataset_title, dataset_type)

    left_columns = left_df.columns.values
    right_columns = right_df.columns.values
    on = list_elements_from_indices(left_columns, on)

    # Not using left_on or right_on for now
    df_joined = left_df.merge(right_df, how=how, on=on, suffixes=[left_suffix, right_suffix])

    return df_joined, new_dataset_title, new_dataset_name, new_dataset_path
