'''
Dataset field properties
'''

import json
import numpy as np
from time import time
from scipy import stats as sc_stats
from flask import current_app

from dive.db import db_access
from dive.task_core import celery, task_app
from dive.data.access import get_data
from dive.tasks.ingestion.type_detection import get_field_types
from dive.tasks.ingestion.analysis import get_unique, get_bin_edges

from celery import states
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)


# TODO Reduce iterations over data elements
@celery.task(bind=True, task_name='field_properties')
def compute_field_properties(self, dataset_id, project_id, track_started=True):
    '''
    Compute field properties of a specific dataset
    Currently only getting properties by column

    Arguments: project_id + dataset ids
    Returns a mapping from dataset_ids to properties

    TODO Clean up and optimize this function
    '''
    self.update_state(state=states.PENDING, meta={'status': 'Computing dataset properties'})

    logger.info("Computing field properties for dataset_id %s", dataset_id)

    with task_app.app_context():
        df = get_data(project_id=project_id, dataset_id=dataset_id)
    df = df.fillna('')

    _names = df.columns.values
    all_properties = [ None ] * len(_names.tolist())

    for i, name in enumerate(_names.tolist()):
        all_properties[i] = {}
        all_properties[i]['index'] = i
        all_properties[i]['name'] = name

    # Statistical properties
    # Only conduct on certain types?
    # start_time = time()
    # df_stats = df.describe()
    # df_stats_dict = json.loads(df_stats.to_json())
    # df_stats_list = []
    # for l in _names:
    #     if l in df_stats_dict:
    #         df_stats_list.append(df_stats_dict[l])
    #     else:
    #         df_stats_list.append({})
    # for i, stats in enumerate(df_stats_list):
    #     all_properties[i]['stats'] = stats
    # describe_time = time() - start_time
    # logger.info("Describing dataset took %s seconds", describe_time)

    ### Getting column types
    start_time = time()
    _types, _type_scores = get_field_types(df)
    for i, _type in enumerate(_types):
        all_properties[i]['type'] = _type
        all_properties[i]['type_scores'] = _type_scores[i]
    type_time = time() - start_time
    logger.info("Field type detection took %s seconds", type_time)

    ### Determining normality
    start_time = time()
    for i, col in enumerate(df):
        _type = _types[i]
        if _type in ["int", "float"]:
            try:
                ## Coerce data vector to float
                d = df[col].astype(np.float)
                normality_result = sc_stats.normaltest(d)
            except ValueError:
                normality_result = None
        else:
            normality_result = None
        all_properties[i]['normality'] = normality_result
    normality_time = time() - start_time
    logger.info("Normality analysis took %s seconds", normality_time)

    ### Detecting if a column is unique
    start_time = time()
    # List of booleans -- is a column composed of unique elements?
    for i, col in enumerate(df):
        all_properties[i]['is_unique'] = detect_unique_list(df[col])
    is_unique_time = time() - start_time
    logger.info("Unique detection took %s seconds", is_unique_time)

    ### Unique values for columns
    start_time = time()
    unique_values = []
    raw_uniqued_values = [ get_unique(df[col]) for col in df ]
    for i, col in enumerate(raw_uniqued_values):
        _type = _types[i]
        # TODO Better classification of uniques
        if _type in ["integer", "float", "datetime"]:
            all_properties[i]['unique_values'] = []
        else:
            all_properties[i]['unique_values'] = col
    get_unique_values_time = time() - start_time

    ### Detect parents
    start_time = time()
    MAX_ROW_THRESHOLD = 100
    for i, col in enumerate(df):
        if i < (len(df.columns) - 1):
            if not all_properties[i]['is_unique'] and all_properties[i]['type'] not in ['float', 'int'] and all_properties[i+1]['type'] not in ['float', 'int']:
                _all_next_col_values = []

                if len(all_properties[i]['unique_values']) > 1:
                    for j, value in enumerate(all_properties[i]['unique_values']):
                        # TODO: be much smarter about sampling columns rather than just taking the first X rows
                        if j > MAX_ROW_THRESHOLD:
                            break

                        sub_df = df.loc[df[all_properties[i]['name']] == value]
                        _next_col_values = sub_df[all_properties[i+1]['name']]

                        _all_next_col_values.extend(set(_next_col_values))

                    _all_next_col_values = [x for x in _all_next_col_values if x != "#"]

                    if len(_all_next_col_values) == len(set(_all_next_col_values)):
                        all_properties[i]['child'] = all_properties[i+1]['name']
                        all_properties[i+1]['is_child'] = True

        if not all_properties[i].get('child'):
            all_properties[i]['child'] = None

        if not all_properties[i].get('is_child'):
            all_properties[i]['is_child'] = False
    get_hierarchies_time = time() - start_time
    logger.info("Get hierarchies time took %s seconds", get_hierarchies_time)

    self.update_state(state=states.SUCCESS)
    return all_properties


# Retrieve entities given datasets
def get_entities(project_id, datasets):
    _properties = get_field_properties(project_id, datasets, get_values = True)
    _all_entities = filter(lambda x: x['type'] not in ['float', 'integer'], _properties)

    parent_entities = filter(lambda x: not x['is_child'], _all_entities)

    for i, _entity in enumerate(parent_entities):
        if _entity['child']:
            _entity['child'] = populate_child_entities(_entity['child'], [], _all_entities)

    return parent_entities


def populate_child_entities(entity_name, child_entities, all_entities):
    _entity = filter(lambda x: x['name'] == entity_name, all_entities)[0]
    if _entity['child']:
        child_entities = populate_child_entities(_entity['child'], child_entities, all_entities)

    return [_entity] + child_entities


# Retrieve entities given datasets
def get_attributes(project_id, datasets):
    attributes = []
    _properties = get_field_properties(project_id, datasets)
    attributes = filter(lambda x: x['type'] in ['float', 'integer'], _properties)
    return attributes


# Detect if a list is comprised of unique elements
def detect_unique_list(l):
    # TODO Vary threshold by number of elements (be smarter about it)
    THRESHOLD = 0.95

    # Comparing length of uniqued elements with original list
    if (len(np.unique(l)) / float(len(l))) >= THRESHOLD:
        return True
    return False


@celery.task(bind=True, ignore_result=True)
def save_field_properties(self, all_properties, dataset_id, project_id):
    ''' Upsert all field properties corresponding to a dataset '''
    self.update_state(state=states.PENDING, meta={'status': 'Saving field properties'})
    field_properties_with_id = []
    for field_properties in all_properties:
        name = field_properties['name']

        with task_app.app_context():
            existing_field_properties = db_access.get_field_properties(project_id, dataset_id, name=name)

        if existing_field_properties:
            logger.info("Updating field property of dataset %s with name %s", dataset_id, name)
            with task_app.app_context():
                field_properties = db_access.update_field_properties(project_id, dataset_id, **field_properties)
        else:
            logger.info("Inserting field property of dataset %s with name %s", dataset_id, name)
            with task_app.app_context():
                field_properties = db_access.insert_field_properties(project_id, dataset_id, **field_properties)
        field_properties_with_id.append(field_properties)
    self.update_state(state=states.SUCCESS, meta={'status': 'Saved field properties'})
