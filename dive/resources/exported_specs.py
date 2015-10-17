from flask import make_response, jsonify
from flask.ext.restful import Resource, reqparse

import logging
import json

from dive.db import db_access
from dive.resources.utilities import format_json


class VisualizationFromExportedSpec(Resource):
    def post(self):
        args = request.json
        # TODO Implement required parameters
        specID = args.get('specID')
        project_id = args.get('project_id')
        dataset_id = args.get('dataset_id')
        spec = args.get('spec')
        conditional = args.get('conditional')

        result = get_viz_data_from_enumerated_spec(spec,
            dataset_id, project_id, data_formats=['visualize', 'table'])

        return make_response(jsonify(format_json(result)))


exportedSpecsGetParser = reqparse.RequestParser()
exportedSpecsGetParser.add_argument('project_id', type=str, required=True)

exportedSpecsPostParser = reqparse.RequestParser()
exportedSpecsPostParser.add_argument('project_id', type=str, required=True, location='json')
exportedSpecsPostParser.add_argument('spec_id', type=str, required=True, location='json')
exportedSpecsPostParser.add_argument('conditionals', type=str, required=True, location='json')
exportedSpecsPostParser.add_argument('config', type=str, required=True, location='json')
class ExportedSpecs(Resource):
    def get(self):
        args = exportedSpecsGetParser.parse_args()
        project_id = args.get('project_id').strip().strip('"')

        exported_specs = db_access.get_exported_specs(project_id)
        return make_response(jsonify(format_json({'result': exported_specs, 'length': len(exported_specs)})))

    def post(self):
        args = exportedSpecsPostParser.parse_args()
        project_id = args.get('project_id')
        spec_id = args.get('spec_id')
        conditionals = json.loads(args.get('conditionals'))
        config = json.loads(args.get('config'))

        result = db_access.insert_exported_spec(project_id, spec_id, conditionals, config)
        return jsonify(format_json(result))
