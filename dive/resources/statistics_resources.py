import time
from flask import make_response, jsonify
from flask.ext.restful import Resource, reqparse

from dive.resources.utilities import format_json
# from dive.tasks.statistics.statistics import getStatisticsFromSpec, timeEstimator

import logging
logger = logging.getLogger(__name__)

#####################################################################
# Endpoint returning estimated time for regression
# INPUT: numInputs, sizeArray, funcArraySize
# OUTPUT: time
#####################################################################

# For inferred visualizations
timeFromParamsPostParser = reqparse.RequestParser()
timeFromParamsPostParser.add_argument('numInputs', type=int, location='json')
timeFromParamsPostParser.add_argument('sizeArray', type=int, location='json')
timeFromParamsPostParser.add_argument('funcArraySize', type=int, location='json')
class RegressionEstimator(Resource):
    def post(self):
        args = request.json
        # TODO Implement required parameters
        numInputs = args.get('numInputs')
        sizeArray = args.get('sizeArray')
        funcArraySize = args.get('funcArraySize')

        result, status = timeEstimator(numInputs, sizeArray, funcArraySize)
        return result


#####################################################################
# Endpoint returning statistical data given a specification
# INPUT: project_id, spec
# OUTPUT: {stat data}
#####################################################################

# For inferred visualizations
statsFromSpecPostParser = reqparse.RequestParser()
statsFromSpecPostParser.add_argument('dataset_id', type=str, location='json')
statsFromSpecPostParser.add_argument('spec', type=str, location='json')
class StatisticsFromSpec(Resource):
    def post(self):
        args = request.json
        # TODO Implement required parameters
        project_id = args.get('project_id')
        spec = args.get('spec')

        print time.clock()

        result, status = getStatisticsFromSpec(spec, project_id)
        # print format_json(result)
        print time.clock()
        return make_response(jsonify(format_json(result)), status)


regressionPostParser = reqparse.RequestParser()
regressionPostParser.add_argument('project_id', type=str, location='json')
regressionPostParser.add_argument('spec', type=str, location='json')
class RegressionFromSpec(Resource):
    def post(self):
        args = regressionPostParser.parse_args()
        project_id = args.get('project_id')
        spec = args.get('spec')
        print project_id, spec
        return


class ComparisonFromSpec(Resource):
    def post(self):
        args = request.get_json()
        project_id = args.get('project_id')
        spec = args.get('spec')
        return


class SegmentationFromSpec(Resource):
    def post(self):
        args = request.get_json()
        project_id = args.get('project_id')
        spec = args.get('spec')
        return
