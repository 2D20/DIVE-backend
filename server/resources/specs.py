from flask import make_response, jsonify
from flask.ext.restful import Resource, reqparse

from app import logger
from .utilities import format_json
from visualization import GeneratingProcedure
from visualization.viz_specs import get_viz_specs
from visualization.viz_data import get_viz_data_from_builder_spec, get_viz_data_from_enumerated_spec

specsGetParser = reqparse.RequestParser()
specsGetParser.add_argument('pID', type=str, required=True)
specsGetParser.add_argument('dID', type=str)
class Specs(Resource):
    def get(self):
        print "[GET] Specs"
        args = specsGetParser.parse_args()
        pID = args.get('pID').strip().strip('"')
        dID = args.get('dID', None)

        specs_by_dID = get_viz_specs(pID, dID)

        return make_response(jsonify(format_json({'specs': specs_by_dID})))


class GeneratingProcedures(Resource):
    ''' Returns a dictionary containing the existing generating procedures. '''
    def get(self):
        result = dict([(gp.name, gp.value) for gp in GeneratingProcedure])
        return make_response(jsonify(format_json(result)))


visualizationGetParser = reqparse.RequestParser()
visualizationGetParser.add_argument('projectTitle', type=str, required=True)
class Visualization(Resource):
    ''' Returns visualization and table data for a given spec'''
    def get(self, vID):
        result = {}

        args = visualizationGetParser.parse_args()
        projectTitle = args.get('projectTitle').strip().strip('"')

        pID = MI.getProjectID(projectTitle)

        find_doc = {'_id': ObjectId(vID)}
        visualizations = MI.getExportedSpecs(find_doc, pID)

        if visualizations:
            spec = visualizations[0]['spec'][0]
            dID = spec['dID']
            formatted_spec = spec
            del formatted_spec['_id']

            result = {
                'spec': spec,
                'visualization': get_viz_data_from_enumerated_spec(spec, dID, pID, data_formats=['visualize', 'table'])
            }

        return make_response(jsonify(format_json(result)))


class VisualizationFromSpec(Resource):
    def post(self):
        args = request.json
        # TODO Implement required parameters
        specID = args.get('specID')
        pID = args.get('pID')
        dID = args.get('dID')
        spec = args.get('spec')
        conditional = args.get('conditional')

        result = get_viz_data_from_enumerated_spec(spec,
            dID, pID, data_formats=['visualize', 'table'])

        return make_response(jsonify(format_json(result)))
