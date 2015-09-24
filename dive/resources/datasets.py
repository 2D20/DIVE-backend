'''
Endpoints for uploading, getting, updating, and deleting datasets
'''
import os
import json
from flask import request, make_response, jsonify
from flask.ext.restful import Resource, reqparse
from celery import chain

from dive.db import db_access
from dive.resources.utilities import format_json
from dive.data.access import get_dataset_sample
from dive.tasks.pipelines import full_pipeline
from dive.tasks.ingestion.upload import upload_file

import logging
logger = logging.getLogger(__name__)


ALLOWED_EXTENSIONS = set(['txt', 'csv', 'tsv', 'xlsx', 'xls', 'json'])


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


# File upload handler
uploadFileParser = reqparse.RequestParser()
uploadFileParser.add_argument('project_id', type=str, required=True)
class UploadFile(Resource):
    '''
    1) Saves file
    2) Triggers data ingestion tasks
    3) Returns dataset_id
    '''
    def post(self):
        logger.info("In upload")
        form_data = json.loads(request.form.get('data'))
        logger.info(form_data)
        project_id = form_data.get('project_id').strip().strip('""')
        file_obj = request.files.get('file')

        if file_obj and allowed_file(file_obj.filename):
            # Get dataset_ids corresponding to file if successful upload
            dataset_ids = upload_file(project_id, file_obj)
            result = {
                'status': 'success',
                'dataset_ids': dataset_ids
            }
            for dataset_id in dataset_ids:
                full_pipeline(dataset_id, project_id).apply_async()
            return make_response(jsonify(format_json(result)))
        return make_response(jsonify(format_json({'status': 'Upload failed'})))


# Datasets list retrieval
datasetsGetParser = reqparse.RequestParser()
datasetsGetParser.add_argument('project_id', type=str, required=True)
datasetsGetParser.add_argument('getStructure', type=bool, required=False, default=False)
class Datasets(Resource):
    ''' Get dataset descriptions or samples '''
    def get(self):
        args = datasetsGetParser.parse_args()
        project_id = args.get('project_id').strip().strip('"')
        logger.info("[GET] Data for project_id: %s" % project_id)

        datasets = db_access.get_datasets(project_id)

        data_list = []
        for d in datasets:
            dataset_data = {
                'title': d.get('title'),
                'file_name': d.get('file_name'),
                'dataset_id': d.get('id')
            }

            if args['getStructure']:
                dataset_data['details'] = db_access.get_dataset_properties(project_id, dataset_id)

            data_list.append(dataset_data)

        return make_response(jsonify(format_json({'status': 'success', 'datasets': data_list})))


# Dataset retrieval, editing, deletion
datasetGetParser = reqparse.RequestParser()
datasetGetParser.add_argument('project_id', type=str, required=True)

datasetDeleteParser = reqparse.RequestParser()
datasetDeleteParser.add_argument('project_id', type=str, required=True)
class Dataset(Resource):
    # Get dataset descriptions or samples
    def get(self, dataset_id):
        args = datasetGetParser.parse_args()
        project_id = args.get('project_id').strip().strip('"')

        dataset = db_access.get_dataset(project_id, dataset_id)

        sample = get_dataset_sample(dataset.get('id'), project_id)

        response = {
            'dataset_id': dataset.get('id'),
            'title': dataset.get('title'),
            'details': sample
        }
        return make_response(jsonify(format_json(response)))


    def delete(self, dataset_id):
        args = datasetDeleteParser.parse_args()
        project_id = args.get('project_id').strip().strip('"')

        # Delete from datasets table
        result = db_access.delete_dataset(project_id, dataset_id)

        # Delete from file ststem
        os.remove(result['path'])
        return jsonify({"message": "Successfully deleted dataset.",
                            "id": int(result['id'])})
