import os

from flask import make_response, current_app
from flask.ext.restful import Resource, reqparse

from dive.db import db_access
from dive.resources.utilities import format_json, jsonify

import logging
logger = logging.getLogger(__name__)


def object_type(j):
    return j


documentGetParser = reqparse.RequestParser()
documentGetParser.add_argument('project_id', type=str, required=True)

documentPutParser = reqparse.RequestParser()
documentPutParser.add_argument('project_id', type=str, required=True, location='json')
documentPutParser.add_argument('content', type=object_type, required=True, location='json')

documentDeleteParser = reqparse.RequestParser()
documentDeleteParser.add_argument('project_id', type=str, required=True)
class Document(Resource):
    '''
    Single document endpoints given a document_id of an existing document
    GET content for one document
    PUT content for one document
    DELETE one document
    '''
    def get(self, document_id):
        logger.info('In get endpoint %s', document_id)
        # print 'about to parse args'
        args = documentGetParser.parse_args()
        project_id = args.get('project_id')
        print 'past args', project_id
        result = db_access.get_document(project_id, document_id)
        return jsonify(format_json(result))

    def put(self, document_id):
        args = documentPutParser.parse_args()
        content = args.get('content')
        project_id = args.get('project_id')
        result = db_access.update_document(project_id, document_id, content)
        return jsonify(format_json(result))

    def delete(self, document_id):
        args = documentDeleteParser.parse_args()
        project_id = args.get('project_id')
        result = db_access.delete_document(project_id, document_id)
        return jsonify(format_json({"message": "Successfully deleted project.",
                            "id": int(result['id'])}))


documentPostParser = reqparse.RequestParser()
documentPostParser.add_argument('project_id', type=str, required=True, location='json')
documentPostParser.add_argument('content', type=object_type, required=True, location='json')
class NewDocument(Resource):
    '''
    POST to add one new document
    '''
    def post(self):
        args = documentPostParser.parse_args()
        content = args.get('content')
        project_id = args.get('project_id')
        result = db_access.create_document(project_id, content)
        return jsonify(format_json(result))
