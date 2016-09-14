import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import ttest_ind
import statsmodels.api as sm
from statsmodels.formula.api import ols
from collections import OrderedDict

from dive.base.db import db_access
from dive.base.data.access import get_data, get_conditioned_data
from dive.worker.ingestion.utilities import get_unique
from dive.worker.statistics.utilities import get_design_matrices, are_variations_equal

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)




def get_anova_boxplot_data(spec, project_id, conditionals={}):
    '''
    For now, spec will be form:
        datasetId
        independentVariables - list names, must be categorical
        dependentVariables - list names, must be numerical
        numBins - number of bins for the independent quantitative variables (if they exist)
    '''
    anova_result = {}

    dependent_variables = spec.get('dependentVariables', [])
    independent_variables = spec.get('independentVariables', [])
    dataset_id = spec.get('datasetId')

    # MIN, Q1, Q3, MAX
    # quantiles = [0.00, 0.25, 0.75, 1.00]

    # Q1 - 1.5IQR, Q1, Q3, Q3 + 1.5IQR
    quantiles = [ 0.25, 0.75 ]

    dependent_variable_names = dependent_variables
    independent_variable_names = [ iv[1] for iv in independent_variables ]

    df = get_data(project_id=project_id, dataset_id=dataset_id)
    df = get_conditioned_data(project_id, dataset_id, df, conditionals)

    # TODO Be smarter about this dropna
    df = df.dropna()  # Remove unclean

    def top_whisker(group):
      Q3 = group.quantile(0.75)
      Q1 = group.quantile(0.25)
      IQR = Q3 - Q1
      return max(group[group <= Q3 + 1.5*IQR])


    def bottom_whisker(group):
      Q3 = group.quantile(0.75)
      Q1 = group.quantile(0.25)
      IQR = Q3 - Q1
      return min(group[group >= Q1 - 1.5*IQR])


    variable_subset = dependent_variable_names + independent_variable_names
    df_subset = df[variable_subset]
    df_grouped = df_subset.groupby(independent_variable_names)
    df_quantiles = df_grouped.quantile(quantiles)
    df_median = df_grouped.median()
    df_mean = df_grouped.mean()
    df_top_whisker = df_grouped.agg(top_whisker)
    df_bottom_whisker = df_grouped.agg(bottom_whisker)

    one_way = (len(independent_variable_names) == 1)

    # { grouped_field_value: { quantile: value } }
    results_grouped_by_highest_level = dict()
    for specifier, value in df_quantiles.to_dict()[dependent_variable_names[0]].iteritems():
        if one_way:
            grouped_field_value, quantile_level = specifier

            top_whisker = df_top_whisker[dependent_variable_names[0]][grouped_field_value]
            bottom_whisker = df_bottom_whisker[dependent_variable_names[0]][grouped_field_value]
            if grouped_field_value in results_grouped_by_highest_level:
                results_grouped_by_highest_level[grouped_field_value][quantile_level] = value
                results_grouped_by_highest_level[grouped_field_value]['top'] = top_whisker
                results_grouped_by_highest_level[grouped_field_value]['bottom'] = bottom_whisker
            else:
                results_grouped_by_highest_level[grouped_field_value] = {
                    quantile_level: value,
                    'top': top_whisker,
                    'bottom': bottom_whisker
                }


    # Sort OrderedDict
    results_grouped_by_highest_level = OrderedDict(results_grouped_by_highest_level)

    print results_grouped_by_highest_level

    # https://github.com/google/google-visualization-issues/issues/782
    final_data_array = [ dependent_variable_names + [ '', '', '', '', 'Median', 'Mean' ] ]
    for grouped_field_value, quantile_value in results_grouped_by_highest_level.iteritems():
        quantile_value_sorted = OrderedDict(quantile_value)

        median = df_median[dependent_variable_names[0]][grouped_field_value]
        mean = df_mean[dependent_variable_names[0]][grouped_field_value]

        data_element = [
            grouped_field_value,
            0.0,
            quantile_value['bottom'],
            quantile_value[0.25],
            median,
            mean,
            quantile_value[0.75],
            quantile_value['top']
        ]

        final_data_array.append(data_element)

    return final_data_array, 200
