from patsy import dmatrices, ModelDesc, Term, LookupFactor, EvalFactor

def create_patsy_model(dependent_variable, independent_variables):
    '''
    Construct and return patsy formula (object representation)
    '''
    lhs = [ Term([LookupFactor(dependent_variable['name'])]) ]
    rhs = [ Term([]) ] + [ Term([LookupFactor(iv['name'])]) for iv in independent_variables ]
    return ModelDesc(lhs, rhs)


def construct_models(dependent_variable, independent_variables):
    '''
    Given dependent and independent variables, return list of patsy model.

    regression_variable_combinations = [ [x], [x, y], [y, z] ]
    models = [ ModelDesc(lhs=y, rhs=[x]), ... ]
    '''
    # Create list of independent variables, one per regression
    regression_variable_combinations = []
    if len(independent_variables) == 2:
        for i, considered_field in enumerate(independent_variables):
            regression_variable_combinations.append([ considered_field ])
    if len(independent_variables) > 2:
        for i, considered_field in enumerate(independent_variables):
            all_fields_except_considered_field = independent_variables[:i] + independent_variables[i+1:]
            regression_variable_combinations.append(all_fields_except_considered_field)
    regression_variable_combinations.append(independent_variables)

    # Create patsy models
    patsy_models = []
    for regression_variable_combination in regression_variable_combinations:
        model = create_patsy_model(dependent_variable, regression_variable_combination)
        patsy_models.append(model)

    return ( regression_variable_combinations, patsy_models )

def recommend_regression_type(dependent_variable):
    dependent_variable_to_regression_type = {
        'c': 'logistic',
        'q': 'linear',
        't': 'linear'
    }

    return dependent_variable_to_regression_type[dependent_variable['general_type']]