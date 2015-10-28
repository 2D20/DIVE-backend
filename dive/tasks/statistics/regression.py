import patsy
import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.discrete import discrete_model

from collections import Counter
from time import time
from itertools import chain, combinations
from operator import add, mul
from math import log10, floor

from dive.tasks.statistics.utilities import sets_normal
from dive.db import db_access
from dive.data.access import get_data

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

def _difference_of_two_lists(l1, l2):
    return [ x for x in l2 if x not in set(l1) ]

# def get_residual_data_array(regression_result):
#     regressions_by_column = regression_result['regressions_by_column']['column_properties']
#     resid =
#     df = get_data(project_id=project_id, dataset_id=dataset_id)
#     df = df.dropna()

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


def get_full_field_documents_from_names(all_fields, names):
    fields = []
    for name in names:
        matched_field = next((f for f in all_fields if f['name'] == name), None)
        if matched_field:
            fields.append(matched_field)
    return fields


def save_regression(spec, result, project_id):
    logger.info("Saving regression")
    existing_regression_doc = db_access.get_regression_from_spec(project_id, spec)
    if existing_regression_doc:
        db_access.delete_regression(project_id, existing_regression_doc['id'])
    inserted_regression = db_access.insert_regression(project_id, spec, result)
    return inserted_regression


def run_regression_from_spec(spec, project_id):
    # 1) Parse and validate arguments
    model = spec.get('model', 'lr')
    independent_variables_names = spec.get('independentVariables', [])
    dependent_variable_name = spec.get('dependentVariable', [])
    estimator = spec.get('estimator', 'ols')
    degree = spec.get('degree', 1)
    weights = spec.get('weights', None)
    functions = spec.get('functions', [])
    dataset_id = spec.get('datasetId')

    if not (dataset_id and dependent_variable_name):
        return "Not passed required parameters", 400

    # Map variables to field documents
    all_fields = db_access.get_field_properties(project_id, dataset_id)
    dependent_variable = next((f for f in all_fields if f['name'] == dependent_variable_name), None)

    print independent_variables_names
    independent_variables = []
    if independent_variables_names:
        independent_variables = get_full_field_documents_from_names(all_fields, independent_variables_names)
    else:
        for field in all_fields:
            if (not (field['general_type'] == 'c' and field['is_unique']) \
                and field['name'] != dependent_variable_name):
                independent_variables.append(field)

    # Determine regression model based on number of type of variables
    variable_types = Counter({
        'independent': { 'q': 0, 'c': 0 },
        'dependent': { 'q': 0, 'c': 0}
    })

    for independent_variable in independent_variables:
        variable_type = independent_variable['general_type']
        variable_types['independent'][variable_type] += 1

    # 2) Access dataset
    df = get_data(project_id=project_id, dataset_id=dataset_id)
    df = df.dropna()

    # 3) Run test based on parameters and arguments
    regression_result = run_cascading_regression(df, independent_variables, dependent_variable, model=model, degree=degree, functions=functions, estimator=estimator, weights=weights)
    return regression_result, 200


def run_cascading_regression(df, independent_variables, dependent_variable, model='lr', degree=1, functions=[], estimator='ols', weights=None):
    # Format data structures
    independent_variable_names = [ iv['name'] for iv in independent_variables ]
    regression_results = {
        'regressions_by_column': [],
        'fields': independent_variable_names,
    }

    num_columns = 0

    # Create list of independent variables, one per regerssion
    regression_variable_combinations = []
    if len(independent_variable_names) > 1:
        for i, considered_field in enumerate(independent_variables):
            regression_variable_combinations.append([ considered_field ])

            all_fields_except_considered_field = independent_variables[:i] + independent_variables[i+1:]
            regression_variable_combinations.append(all_fields_except_considered_field)

    regression_variable_combinations.append(independent_variables)

    for considered_independent_variables in regression_variable_combinations:
        regression_result = {}
        num_columns += 1

        # Run regression
        model_result = multivariate_linear_regression(df, considered_independent_variables, dependent_variable, estimator, weights)

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

    return regression_results


def format_properties_by_field(fields, properties):
    propertiesByField = []

    for (i, field) in enumerate(fields):
        formattedProperty = {
            'field': field
        }

        for _property in properties:
            formattedProperty[_property.get('type')] = _property.get('data').get(field)

        propertiesByField.append(formattedProperty)

    return propertiesByField


def _parse_confidence_intervals(model_result):
    conf_int = model_result.conf_int().transpose().to_dict()

    parsed_conf_int = {}
    for field, d in conf_int.iteritems():
        parsed_conf_int[field] = [ d[0], d[1] ]
    return parsed_conf_int


def create_regression_formula(independent_variables, dependent_variable):
    formula = '%s ~ ' % (dependent_variable['name'])
    terms = []
    for independent_variable in independent_variables:
        if independent_variable['general_type'] == 'q':
            term = independent_variable['name']
        else:
            term = 'C(%s)' % (independent_variable['name'])
        terms.append(term)
    concatenated_terms = ' + '.join(terms)
    formula = formula + concatenated_terms
    formula = formula.encode('ascii')

    logger.info("Regression formula %s:", formula)
    return formula


def multivariate_linear_regression(df, independent_variables, dependent_variable, estimator, weights=None):
    formula = create_regression_formula(independent_variables, dependent_variable)
    y, X = patsy.dmatrices(formula, df, return_type='dataframe')

    if dependent_variable['general_type'] == 'q':
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
            'r_squared': model_result.rsquared,
            'r_squared_adj': model_result.rsquared_adj,
            'fTest': model_result.fvalue,
            'resid': model_result.resid.tolist()
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
    # Restructure field properties dict from
    # { property: { field: value }} -> [ field: field, properties: { property: value } ]
    properties_by_field = []
    for field in independent_variable_names:
        properties = { 'field': field, 'properties': {} }
        for prop_type, field_names_and_values in regression_field_properties.iteritems():
            if field in field_names_and_values:
                properties['properties'][prop_type] = field_names_and_values[field]
        properties_by_field.append(properties)

    return {
        'constants': constants,
        'properties_by_field': properties_by_field,
        'total_regression_properties': total_regression_properties
    }


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
