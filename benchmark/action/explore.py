import logging
import time
from benchmark.action.base_action import Action

LOG = logging.getLogger(__name__)


class Explore(Action):

    EXPLORE_TASK_PENDING = 'PENDING'

    ACTION_ARG_WHITELIST = ['dive_url', 'delay']

    def __init__(self, dive_url, delay=0):
        self._dive_url = dive_url
        self._delay = delay
        super(Explore, self).__init__()

    def run(self, args):
        LOG.info('Starting upload action')
        LOG.info('Delaying {0} seconds'.format(str(self._delay)))
        time.sleep(self._delay)
        LOG.info('Finished delay')
        projects_response = args['session'].get('%s/projects/v1/projects?private=True' % self._dive_url)
        projects = projects_response.json()['projects']
        for project in projects:
            for dataset in project['includedDatasets']:
                start_time = time.time()
                specs_response = args['session'].post('%s/specs/v1/specs' % self._dive_url, json={
                    'project_id': dataset['projectId'],
                    'dataset_id': dataset['id'],
                    'field_agg_pairs': [],
                    'recommendation_types': ['exact'],
                    'conditions': {}
                })
                task_id = specs_response.json()['taskId']
                task_status = self.EXPLORE_TASK_PENDING
                while task_status == self.EXPLORE_TASK_PENDING:
                    time.sleep(0.5)
                    status_response = args['session'].get('{0}/tasks/v1/result/{1}'.format(self._dive_url, task_id))
                    task_status = status_response.json()['state']
                end_time = time.time()
                LOG.info("Explore of projectId: {0}, for datasetId: {1}, named dataset: {2}, took {3} seconds"
                         .format(dataset['projectId'], dataset['id'], dataset['title'], str(end_time - start_time)))
