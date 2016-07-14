'''
Endpoints for updating fields
'''
import os
import json
from flask import request, make_response
from flask.ext.restful import Resource, reqparse

from dive.db import db_access
from dive.tasks.ingestion import quantitative_types, categorical_types, temporal_types, specific_to_general_type
from dive.resources.serialization import jsonify

import logging
logger = logging.getLogger(__name__)


def object_type(j):
    return j


fieldPostParser = reqparse.RequestParser()
fieldPostParser.add_argument('project_id', type=str, required=True, location='json')
fieldPostParser.add_argument('type', type=object_type, location='json')
fieldPostParser.add_argument('isId', type=bool, location='json')
class Field(Resource):
    def post(self, field_id):
        args = fieldPostParser.parse_args()
        project_id = args.get('project_id')
        field_type = args.get('type')
        field_is_id = args.get('isId')

        if field_type:
            if (field_type not in quantitative_types) \
                and (field_type not in categorical_types) \
                and (field_type not in temporal_types):
                return make_response(jsonify({'status': 'Invalid field type.'}))
            general_type = specific_to_general_type[field_type]

            field_property_document = \
                db_access.update_field_properties_type_by_id(project_id, field_id, field_type, general_type)

        if field_is_id != None:
            field_property_document = \
                db_access.update_field_properties_is_id_by_id(project_id, field_id, field_is_id)
            
        return make_response(jsonify(field_property_document))
