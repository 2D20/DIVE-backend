from itertools import combinations
from dive.tasks.visualization import GeneratingProcedure as GP, TypeStructure as TS, \
    TermType, aggregation_functions, VizType as VT
from dive.tasks.visualization.marginal_spec_functions import elementwise_functions, binning_procedures


from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)


def multi_c(c_fields):
    logger.debug("F: Multi C")
    specs = []

    # Count of one field given another
    # E.g. count of position by gender
    for (c_field_a, c_field_b) in combinations(c_fields, 2):
        c_label_a, c_label_b = c_field_a['name'], c_field_b['name']
        if (c_field_a['is_unique'] or c_field_b['is_unique']):
            continue
        spec = {
            'generating_procedure': GP.MULTIGROUP_COUNT.value,
            'type_structure': TS.liC_Q.value,
            'viz_types': [ VT.STACKED_BAR.value ],
            'field_ids': [ c_field_a['id'], c_field_b['id'] ],

            'args': {
                'field_a': c_field_a,
                'field_b': c_field_b,
            },
            'meta': {
                'desc': 'Count by %s then %s' % (c_label_a, c_label_b),
                'construction': [
                    { 'string': 'Count', 'type': TermType.OPERATION.value },
                    { 'string': 'by', 'type': TermType.PLAIN.value },
                    { 'string': c_label_a, 'type': TermType.FIELD.value },
                    { 'string': 'then', 'type': TermType.PLAIN.value },
                    { 'string': c_label_b, 'type': TermType.FIELD.value },
                ],
                'labels': {
                    'x': 'Grouping by %s then %s' % (c_label_a, c_label_b),
                    'y': 'Count'
                },
            }
        }
        specs.append(spec)
    return specs


def multi_q(q_fields):
    logger.debug("B: Multi Q - %s", [f['name'] for f in q_fields])
    specs = []

    #Function on pairs of columns
    for (q_field_a, q_field_b) in combinations(q_fields, 2):
        q_label_a = q_field_a['name']
        q_label_b = q_field_b['name']

        # Raw comparison
        raw_comparison_spec = {
            'generating_procedure': GP.VAL_VAL.value,
            'type_structure': TS.Q_Q.value,
            'field_ids': [ q_field_a['id'], q_field_b['id'] ],
            'viz_types': [ VT.SCATTER.value ],
            'args': {
                'field_a': q_field_a,
                'field_b': q_field_b
            },
            'meta': {
                'desc': '%s vs. %s' % (q_label_a, q_label_b),
                'construction': [
                    { 'string': q_label_a, 'type': TermType.FIELD.value },
                    { 'string': 'vs.', 'type': TermType.PLAIN.value },
                    { 'string': q_label_b, 'type': TermType.FIELD.value },
                ]
            }
        }
        specs.append(raw_comparison_spec)
    return specs


def multi_t(t_fields):
    logger.debug('Multi T - %s', [f['name'] for f in t_fields])
    specs = []
    return specs
