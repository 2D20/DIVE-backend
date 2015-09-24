'''
Get and compute whole-dataset properties
'''
import pandas as pd

from dive.db import db_access
from dive.task_core import celery, task_app
from dive.data.access import get_data, get_delimiter
from dive.data.in_memory_data import InMemoryData as IMD
from dive.tasks.ingestion.type_detection import get_column_types, detect_time_series

import logging
logger = logging.getLogger("__name__")


@celery.task(bind=True)
def compute_dataset_properties(self, dataset_id, project_id, path=None):
    ''' Compute and return dictionary containing whole
    import pandas as pd-dataset properties '''
    self.update_state(state='STARTED', meta={'status': 'Computing dataset properties'})

    if not path:
        with task_app.app_context():
            path = db_access.get_dataset(project_id, dataset_id)['path']
    df = get_data(path=path).fillna('')  # TODO turn fillna into an argument
    n_rows, n_cols = df.shape
    field_names = df.columns.values.tolist()
    field_types = get_column_types(df)

    time_series = detect_time_series(df)
    if time_series:
        structure = 'wide'
    else:
        structure = 'long'

    properties = {
        'n_rows': n_rows,
        'n_cols': n_cols,
        'field_names': field_names,
        'field_types': field_types,
        'field_accessors': [ i for i in range(0, n_cols) ],
        'structure': structure,
        'is_time_series': time_series,
    }

    self.update_state(state='STARTED')
    return properties


@celery.task
def save_dataset_properties(properties, dataset_id, project_id):
    with task_app.app_context():
        existing_dataset_properties = db_access.get_dataset_properties(project_id, dataset_id)
    if existing_dataset_properties:
        logger.info("Updating field property of dataset %s", dataset_id)
        with task_app.app_context():
            dataset_properties = db_access.update_dataset_properties(project_id, dataset_id, **properties)
    else:
        logger.info("Inserting field property of dataset %s", dataset_id)
        with task_app.app_context():
            dataset_properties = db_access.insert_dataset_properties(project_id, dataset_id, **properties)
    return dataset_properties
