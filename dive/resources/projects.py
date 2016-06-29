import os
import shutil

from flask import make_response, current_app
from flask.ext.restful import Resource, reqparse, marshal_with
from flask.ext.login import login_required


from dive.db import db_access
from dive.db.accounts import load_account
from dive.auth.account import project_auth
from dive.resources.serialization import jsonify

import logging
logger = logging.getLogger(__name__)


projectPutParser = reqparse.RequestParser()
projectPutParser.add_argument('title', type=str, required=False)
projectPutParser.add_argument('description', type=str, required=False)
class Project(Resource):
    '''
    Single Project endpoints given a project_id
    GET data for one project
    PUT data for one project
    DELETE one project
    '''
    @login_required
    def get(self, project_id):
        has_project_access, auth_message = project_auth(project_id)
        if not has_project_access: return auth_message

        result = db_access.get_project(project_id)
        return jsonify(result)


    def put(self, project_id):
        args = projectPutParser.parse_args()
        title = args.get('title')
        description = args.get('description')
        result = db_access.update_project(project_id, title=title, description=description)
        return jsonify(result)

    def delete(self, project_id):
        result = db_access.delete_project(project_id)
        project_dir = os.path.join(current_app.config['UPLOAD_DIR'], str(result['id']))
        if os.path.isdir(project_dir):
            shutil.rmtree(project_dir)
        return jsonify({"message": "Successfully deleted project.",
                            "id": result['id']})


projectsGetParser = reqparse.RequestParser()
projectsGetParser.add_argument('user_id', type=int, required=False)
projectsGetParser.add_argument('preloaded', type=bool, default=False)
projectsGetParser.add_argument('private', type=bool, default=False)

projectsPostParser = reqparse.RequestParser()
projectsPostParser.add_argument('title', type=str, location='json', required=False)
projectsPostParser.add_argument('description', type=str, location='json', required=False)
projectsPostParser.add_argument('anonymous', type=bool, location='json', required=False, default=False)
projectsPostParser.add_argument('private', type=bool, location='json', required=False, default=True)
projectsPostParser.add_argument('user_id', type=int, required=False)
class Projects(Resource):
    '''
    GET list of all projects
    POST to add new projects
    '''
    def get(self):
        args = projectsGetParser.parse_args()
        user_id = args.get('user_id')
        preloaded = args.get('preloaded')
        private = args.get('private')

        query_args = {}
        if 'preloaded' in args:
            query_args['preloaded'] = preloaded

        if 'private' in args:
            query_args['private'] = private

        if 'user_id' in args and user_id:
            user = load_account(user_id)
            if user.is_admin():
                del query_args['private']
            if not user.is_admin() and not preloaded:
                query_args['user_id'] = user_id

        return jsonify({'projects': db_access.get_projects(**query_args)})

    # Create project, initialize directories and collections
    def post(self):
        args = projectsPostParser.parse_args()
        title = args.get('title')
        description = args.get('description')
        user_id = args.get('user_id')
        anonymous = args.get('anonymous')
        private = args.get('private')

        result = db_access.insert_project(
            title=title,
            description=description,
            user_id=user_id,
            private=private,
            preloaded=False,
            anonymous=anonymous
        )

        new_project_id = result['id']
        db_access.create_document(new_project_id)

        project_dir = os.path.join(current_app.config['UPLOAD_DIR'], str(result['id']))
        if os.path.isdir(project_dir):
            os.mkdir(project_dir)

        return jsonify(result)
