'''
'''
import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.discrete import discrete_model
from patsy import dmatrices, ModelDesc, Term, LookupFactor, EvalFactor

from collections import Counter, OrderedDict
from time import time
from itertools import chain, combinations
from operator import add, mul
from math import log10, floor

from dive.db import db_access
from dive.data.access import get_data
from dive.task_core import celery, task_app
from dive.tasks.statistics.utilities import sets_normal, difference_of_two_lists
from dive.resources.serialization import replace_unserializable_numpy

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)


def run_regression_from_spec(spec, project_id):
    '''
    Wrapper function for five discrete steps:
    1) Parse arguments (in this function)
    2) Loading data from DB for fields and dataframe
    3) Construct / recommend models given those fields
    4) Run regressions described by those models
    5) Format results
    '''
    # 1) Parse and validate arguments
    model = spec.get('model', 'lr')
    independent_variables_names = spec.get('independentVariables', [])
    dependent_variable_name = spec.get('dependentVariable', [])
    estimator = spec.get('estimator', 'ols')
    degree = spec.get('degree', 1)  # need to find quantitative, categorical
    weights = spec.get('weights', None)
    functions = spec.get('functions', [])
    dataset_id = spec.get('datasetId')

    if not (dataset_id and dependent_variable_name):
        return 'Not passed required parameters', 400

    dependent_variable, independent_variables, df = \
        load_data(dependent_variable_name, independent_variables_names, dataset_id, project_id)

    models = construct_models(dependent_variable, independent_variables)
    raw_results = run_models(models)
    evaluate_results()
    format_results()
    return


def load_data(dependent_variable_name, independent_variables_names, dataset_id, project_id):
    '''
    Load DF and full field documents
    '''
    # Map variables to field documents
    with task_app.app_context():
        all_fields = db_access.get_field_properties(project_id, dataset_id)
    dependent_variable = next((f for f in all_fields if f['name'] == dependent_variable_name), None)

    independent_variables = []
    if independent_variables_names:
        independent_variables = get_full_field_documents_from_field_names(all_fields, independent_variables_names)
    else:
        for field in all_fields:
            if (not (field['general_type'] == 'c' and field['is_unique']) \
                and field['name'] != dependent_variable_name):
                independent_variables.append(field)

    # 2) Access dataset
    with task_app.app_context():
        df = get_data(project_id=project_id, dataset_id=dataset_id)
    df = df.dropna(axis=0, how='any')

    return dependent_variable, independent_variables, df


def get_variable_type_counts(dependent_variables, independent_variables):
    '''
    Return count of C, T, Q variables
    '''
    variable_types = Counter({
        'independent': { 'q': 0, 'c': 0, 't': 0 },
        'dependent': { 'q': 0, 'c': 0, 't': 0 }
    })

    for dependent_variable in dependent_variables:
        dependent_variable_type = dependent_variable['general_type']
        variable_types['dependent'][dependent_variable_type] += 1

    for independent_variable in independent_variables:
        independent_variable_type = independent_variable['general_type']
        variable_types['independent'][independent_variable_type] += 1

    return variable_types


def run_regression_from_spec(spec, project_id):
    '''
    Wrapper function taking in a regression spec and returning formatted result.
    Mostly parses arguments, loads relevant data.
    '''

    # 3) Run test based on parameters and arguments
    regression_result = run_cascading_regression(df, independent_variables, dependent_variable, model=model, degree=degree, functions=functions, estimator=estimator, weights=weights)
    return regression_result, 200


def construct_models(dependent_variable, independent_variables):
    '''
    Given dependent and independent variables, return list of patsy model.

    regression_variable_combinations = [ [x], [x, y], [y, z] ]
    models = [ ModelDesc(lhs=y, rhs=[x]), ... ]
    '''
    # Create list of independent variables, one per regression
    regression_variable_combinations = []
    if len(independent_variable_names) == 2:
        for i, considered_field in enumerate(independent_variables):
            regression_variable_combinations.append([ considered_field ])
    if len(independent_variable_names) > 2:
        for i, considered_field in enumerate(independent_variables):
            all_fields_except_considered_field = independent_variables[:i] + independent_variables[i+1:]
            regression_variable_combinations.append(all_fields_except_considered_field)
    regression_variable_combinations.append(independent_variables)

    # Create patsy models
    models = []
    for regression_variable_combination in regression_variable_combinations:
        model = create_patsy_model(dependent_variable, independent_variables)
        models.append(model)

    return models


def create_patsy_model(dependent_variable, independent_variables):
    '''
    Construct and return patsy formula (object representation)
    '''
    lhs = [ Term([LookupFactor(dependent_variable['name'])]) ]
    rhs = [ Term([]) ] + [ Term([LookupFactor(iv['name'])]) for iv in independent_variables ]
    return ModelDesc(lhs, rhs)





def get_full_field_documents_from_field_names(all_fields, names):
    fields = []
    for name in names:
        matched_field = next((f for f in all_fields if f['name'] == name), None)
        if matched_field:
            fields.append(matched_field)
    return fields


def save_regression(spec, result, project_id):
    with task_app.app_context():
        existing_regression_doc = db_access.get_regression_from_spec(project_id, spec)
        if existing_regression_doc:
            db_access.delete_regression(project_id, existing_regression_doc['id'])
        result = replace_unserializable_numpy(result)
        inserted_regression = db_access.insert_regression(project_id, spec, result)
        return inserted_regression


def run_models(df, models, model='lr', degree=1, functions=[], estimator='ols', weights=None):
    # Initialize returned data structures
    num_columns = 0
    independent_variable_names = [ iv['name'] for iv in independent_variables ]
    regression_fields_dict = OrderedDict([(ivn, None) for ivn in independent_variable_names ])
    regression_results = {
        'regressions_by_column': [],
    }

    # Construct models
    regression_variable_combinations = construct_regression_model(dependent_variable, independent_variables)

    # Iterate over and run each models
    for considered_independent_variables in regression_variable_combinations:
        num_columns += 1
        regression_result = {}

        # Run regression
        model_result = multivariate_linear_regression(df, considered_independent_variables, dependent_variable, estimator, weights)

        # Move categorical field values to higher level
        for field_name, field_values in model_result['categorical_field_values'].iteritems():
            regression_fields_dict[field_name] = field_values


        # Test regression
        regression_stats = None
        if model_result['total_regression_properties'].get('resid'):
            dep_data = df[dependent_variable['name']]
            regression_stats = test_regression_fit(model_result['total_regression_properties']['resid'], dep_data)

        # Format results
        field_names = [ civ['name'] for civ in considered_independent_variables ]

        regression_result = {
            'regressed_fields': field_names,
            'regression': {
                'constants': model_result['constants'],
                'properties_by_field': model_result['properties_by_field']
            },
            'column_properties': model_result['total_regression_properties']
        }
        regression_results['regressions_by_column'].append(regression_result)
        if regression_stats:
            regression_result['regression']['stats'] = regression_stats

    regression_results['num_columns'] = num_columns

    # Convert regression fields dict into collection
    regression_fields_collection = []
    for field, values in regression_fields_dict.iteritems():
        regression_fields_collection.append({
            'name': field,
            'values': values
        })
    regression_results['fields'] = regression_fields_collection

    return regression_results


def _parse_confidence_intervals(model_result):
    conf_int = model_result.conf_int().transpose().to_dict()

    parsed_conf_int = {}
    for field, d in conf_int.iteritems():
        parsed_conf_int[field] = [ d[0], d[1] ]
    return parsed_conf_int

def multivariate_linear_regression(df, independent_variables, dependent_variable, estimator, weights=None):
    y, X = dmatrices(model, df, return_type='dataframe')

    if dependent_variable['general_type'] in [ 'q', 't' ]:
        model_result = sm.OLS(y, X).fit()

        p_values = model_result.pvalues.to_dict()
        t_values = model_result.tvalues.to_dict()
        params = model_result.params.to_dict()
        ste = model_result.bse.to_dict()
        conf_ints = _parse_confidence_intervals(model_result)

        constants = {
            'p_value': p_values.get('Intercept'),
            't_value': t_values.get('Intercept'),
            'coefficient': params.get('Intercept'),
            'standard_error': ste.get('Intercept'),
            'conf_int': conf_ints.get('Intercept')
        }

        regression_field_properties = {
            'p_value': p_values,
            't_value': t_values,
            'coefficient': params,
            'standard_error': ste,
            'conf_int': conf_ints
        }

        total_regression_properties = {
            'aic': model_result.aic,
            'bic': model_result.bic,
            'dof': model_result.nobs,
            'r_squared': model_result.rsquared,
            'r_squared_adj': model_result.rsquared_adj,
            'f_test': model_result.fvalue,
            # 'resid': model_result.resid.tolist()
        }

    elif dependent_variable['general_type'] == 'c':
        model_result = discrete_model.MNLogit(y, X).fit(maxiter=100, disp=False)

        p_values = model_result.pvalues[0].to_dict()
        t_values = model_result.tvalues[0].to_dict()
        params = model_result.params[0].to_dict()
        ste = model_result.bse[0].to_dict()

        constants = {
            'p_value': p_values.get('Intercept'),
            't_value': t_values.get('Intercept'),
            'coefficient': params.get('Intercept'),
            'standard_error': ste.get('Intercept')
        }

        regression_field_properties = {
            'p_value': p_values,
            't_value': t_values,
            'coefficient': params,
            'standard_error': ste
        }

        total_regression_properties = {
            'aic': model_result.aic,
            'bic': model_result.bic,
        }

    independent_variable_names = [ iv['name'] for iv in independent_variables ]

    categorical_field_values = {}

    # Restructure field properties dict from
    # { property: { field: value }} -> [ field: field, properties: { property: value } ]
    properties_by_field_dict = {}

    for prop_type, field_names_and_values in regression_field_properties.iteritems():
        for field_name, value in field_names_and_values.iteritems():
            if field_name in properties_by_field_dict:
                properties_by_field_dict[field_name][prop_type] = value
            else:
                properties_by_field_dict[field_name] = { prop_type: value }

    properties_by_field_collection = []
    for field_name, properties in properties_by_field_dict.iteritems():
        new_doc = {
            'field': field_name
        }
        base_field, value_field = _get_fields_categorical_variable(field_name)
        new_doc['base_field'] = base_field
        new_doc['value_field'] = value_field
        new_doc.update(properties)

        # Update list mapping categorical fields to values
        if value_field:
            if base_field not in categorical_field_values:
                categorical_field_values[base_field] = [ value_field ]
            else:
                categorical_field_values[base_field].append(value_field)

        properties_by_field_collection.append(new_doc)

    return {
        'constants': constants,
        'categorical_field_values': categorical_field_values,
        'properties_by_field': properties_by_field_collection,
        'total_regression_properties': total_regression_properties
    }


def _get_fields_categorical_variable(s):
    '''
    Parse base and value fields out of statsmodels categorical encoding
    e.g. 'department[T.Engineering]' -> [ department, Engineering ]
    '''
    base_field = s
    value_field = None
    if '[' in s:
        base_field = s.split('[')[0]
        value_field = s.split('[T.')[1].strip(']')
        print base_field, value_field
    return base_field, value_field

def test_regression_fit(residuals, actual_y):
    '''
    Run regression tests
    Tests how well the regression line predicts the data
    '''
    predicted_y = np.array(residuals) + np.array(actual_y)

    # Non-parametric tests (chi-square and KS)
    chisquare = stats.chisquare(predicted_y, actual_y)
    kstest = stats.ks_2samp(predicted_y, actual_y)
    results = {
        'chi_square': {
            'test_statistic': chisquare[0],
            'p_value': chisquare[1]
        },
        'ks_test': {
            'test_statistic': kstest[0],
            'p_value': kstest[1]
        }
    }

    if len(set(residuals)) > 1:
        wilcoxon = stats.wilcoxon(residuals)
        results['wilcoxon'] = {
            'testStatistic': wilcoxon[0],
            'pValue': wilcoxon[1]
        }

    if sets_normal(0.2, residuals, actual_y):
        t_test_result = stats.ttest_1samp(residuals, 0)
        results['t_test'] = {
            'test_statistic': t_test_result[0],
            'p_value': t_test_result[1]
        }

    return results


def get_contribution_to_r_squared_data(regression_result):
    regressions_by_column = regression_result['regressions_by_column']

    considered_fields_length_to_names = {}
    fields_to_r_squared_adj = {}

    for regression_by_column in regressions_by_column:
        column_properties = regression_by_column['column_properties']
        r_squared_adj = column_properties['r_squared_adj']
        fields = regression_by_column['regressed_fields']

        if len(fields) not in considered_fields_length_to_names:
            considered_fields_length_to_names[len(fields)] = [ fields ]
        else:
            considered_fields_length_to_names[len(fields)].append(fields)
        fields_to_r_squared_adj[str(fields)] = r_squared_adj

    max_fields_length = max(considered_fields_length_to_names.keys())
    all_fields = considered_fields_length_to_names[max_fields_length][0]
    all_fields_r_squared_adj = fields_to_r_squared_adj[str(all_fields)]

    if max_fields_length <= 1:
        return

    maximum_r_squared_adj = max(fields_to_r_squared_adj.values())

    data_array = [['Field', 'Marginal R-squared']]

    all_except_one_regression_fields = considered_fields_length_to_names[max_fields_length - 1]
    for all_except_one_regression_fields in all_except_one_regression_fields:
        regression_r_squared_adj = fields_to_r_squared_adj[str(all_except_one_regression_fields)]

        marginal_field = _difference_of_two_lists(all_except_one_regression_fields, all_fields)[0]
        marginal_r_squared_adj = all_fields_r_squared_adj - regression_r_squared_adj
        data_array.append([ marginal_field, marginal_r_squared_adj])

    return data_array
