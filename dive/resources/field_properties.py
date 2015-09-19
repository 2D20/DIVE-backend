from flask import make_response, jsonify
from flask.ext.restful import Resource, reqparse

import logging
logger = logging.getLogger(__name__)

from dive.resources.utilities import format_json
from dive.data.field_properties import get_field_properties, get_entities, get_attributes, compute_field_properties

############################
# Property (begins processing on first client API call)
# Determine: types, hierarchies, uniqueness (subset of distributions), ontology, distributions
# INPUT: project_id, dataset_id
# OUTPUT: properties corresponding to that dataset_id
############################
fieldPropertiesGetParser = reqparse.RequestParser()
fieldPropertiesGetParser.add_argument('project_id', type=str, required=True)
fieldPropertiesGetParser.add_argument('dataset_id', type=str, required=True)
class FieldProperties(Resource):
    def get(self):
        logger.info("[GET] Field Properties")
        args = fieldPropertiesGetParser.parse_args()
        project_id = args.get('project_id').strip().strip('"')
        dataset_id = args.get('dataset_id')

        # TODO Make this work with multiple dataset_ids
        dataset_ids = [ dataset_id ]
        field_properties = get_field_properties(project_id, dataset_ids, get_values=False, flatten=True)
        return make_response(jsonify(format_json(field_properties)))
