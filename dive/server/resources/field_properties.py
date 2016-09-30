import json

from flask import make_response
<<<<<<< HEAD:dive/resources/field_properties.py
from flask_restful import Resource, reqparse, marshal, fields, marshal_with
=======
from flask.ext.restful import Resource, reqparse, marshal, fields, marshal_with
from flask.ext.login import login_required

from dive.base.db import db_access
from dive.base.serialization import jsonify
from dive.worker.ingestion.field_properties import compute_all_field_properties
>>>>>>> master:dive/server/resources/field_properties.py


import logging
logger = logging.getLogger(__name__)


fieldPropertiesGetParser = reqparse.RequestParser()
fieldPropertiesGetParser.add_argument('project_id', type=str, required=True)
fieldPropertiesGetParser.add_argument('dataset_id', type=str, required=True)
fieldPropertiesGetParser.add_argument('group_by', type=str)
class FieldProperties(Resource):
    '''
    Args: project_id, dataset_id
    Returns: properties corresponding to that dataset_id
    '''
    @login_required
    def get(self):
        args = fieldPropertiesGetParser.parse_args()
        project_id = args.get('project_id').strip().strip('"')
        dataset_id = args.get('dataset_id')
        group_by = args.get('group_by')

        field_properties = db_access.get_field_properties(project_id, dataset_id)
        interaction_terms = db_access.get_interaction_terms(project_id, dataset_id)

        if group_by:
            result = {}
            for fp in field_properties:
                fp_group_by = fp[group_by]
                if fp_group_by in result:
                    result[fp_group_by].append(fp)
                else:
                    result[fp_group_by] = [fp]
        else:
            result = {'field_properties': field_properties}

        result['interactionTerms'] = interaction_terms
        return make_response(jsonify(result))
