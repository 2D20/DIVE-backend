'''
Module containing functions and Data Access Objects for accessing the database.
Parameters in, JSONable objects out.

Mainly used to separate session management from models, and to provide uniform
db interfaces to both the API and compute layers.
'''

from flask import abort
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from dive.core import db
from dive.db import ModelName, row_to_dict
from dive.db.models import Project, Dataset, Dataset_Properties, Field_Properties, \
    Spec, Exported_Spec, Regression, Exported_Regression, Interaction_Term, Group, User, \
    Relationship, Document, Summary, Exported_Summary, Correlation, Exported_Correlation
from dive.resources import ContentType

import logging
logger = logging.getLogger(__name__)


################
# Projects
# https://github.com/sloria/PythonORMSleepy/blob/master/sleepy/api_sqlalchemy.py
################
def get_project(project_id):
    project = Project.query.get_or_404(int(project_id))
    return row_to_dict(project)

def get_projects(**kwargs):
    projects = Project.query.filter_by(**kwargs).all()
    return [ row_to_dict(project) for project in projects ]

def insert_project(**kwargs):
    project = Project(
        **kwargs
    )
    db.session.add(project)
    db.session.commit()
    return row_to_dict(project)

def update_project(project_id, **kwargs):
    project = Project.query.get_or_404(int(project_id))

    for k, v in kwargs.iteritems():
        setattr(project, k, v)

    db.session.add(project)
    db.session.commit()
    return row_to_dict(project)

def delete_project(project_id):
    project = Project.query.get_or_404(int(project_id))
    db.session.delete(project)
    db.session.commit()
    return row_to_dict(project)

################
# Datasets
################
def get_dataset(project_id, dataset_id):
    # http://stackoverflow.com/questions/2128505/whats-the-difference-between-filter-and-filter-by-in-sqlalchemy
    logger.debug("Get dataset with project_id %s and dataset_id %s", project_id, dataset_id)
    try:
        dataset = Dataset.query.filter_by(project_id=project_id, id=dataset_id).one()
        return row_to_dict(dataset)

    # TODO Decide between raising error and aborting with 404
    except NoResultFound, e:
        logger.error(e)
        return None

    except MultipleResultsFound, e:
        logger.error(e)
        raise e

def get_datasets(project_id, **kwargs):
    datasets = Dataset.query.filter_by(project_id=project_id, **kwargs).all()
    return [ row_to_dict(dataset) for dataset in datasets ]

def insert_dataset(project_id, **kwargs):
    logger.debug("Insert dataset with project_id %s", project_id)

    dataset = Dataset(
        project_id=project_id,
        **kwargs
    )
    db.session.add(dataset)
    db.session.commit()
    return row_to_dict(dataset)


def delete_dataset(project_id, dataset_id):
    dataset = Dataset.query.filter_by(project_id=project_id, id=dataset_id).one()
    db.session.delete(dataset)
    db.session.commit()
    return row_to_dict(dataset)


################
# Dataset Properties
################
def get_dataset_properties(project_id, dataset_id):
    try:
        dataset_properties = Dataset_Properties.query.filter_by(project_id=project_id, dataset_id=dataset_id).one()
        return row_to_dict(dataset_properties)
    except NoResultFound, e:
        return None
    except MultipleResultsFound, e:
        raise e

# TODO Do an upsert?
def insert_dataset_properties(project_id, dataset_id, **kwargs):
    dataset_properties = Dataset_Properties(
        dataset_id = dataset_id,
        project_id = project_id,
        **kwargs
    )
    db.session.add(dataset_properties)
    db.session.commit()
    return row_to_dict(dataset_properties)

def update_dataset_properties(project_id, dataset_id, **kwargs):

    dataset_properties = Dataset_Properties.query.filter_by(project_id=project_id,
        dataset_id=dataset_id,
        ).one()

    for k, v in kwargs.iteritems():
        setattr(dataset_properties, k, v)

    db.session.add(dataset_properties)
    db.session.commit()
    return row_to_dict(dataset_properties)

def delete_dataset_properties(project_id, dataset_id):
    dataset_properties = Dataset_Properties.query.filter_by(project_id=project_id, id=dataset_id).one()
    db.session.delete(dataset_properties)
    db.session.commit()
    return row_to_dict(dataset_properties)

################
# Field Properties
#
# TODO Write functions dealing with one vs many field properties
################
def get_field_properties(project_id, dataset_id, **kwargs):
    result = Field_Properties.query.filter_by(project_id=project_id, dataset_id=dataset_id, **kwargs).all()
    field_properties = [ row_to_dict(r) for r in result ]
    return field_properties


def insert_field_properties(project_id, dataset_id, **kwargs):
    field_properties = Field_Properties(
        dataset_id = dataset_id,
        project_id = project_id,
        **kwargs
    )
    db.session.add(field_properties)
    db.session.commit()
    return row_to_dict(field_properties)


def update_field_properties(project_id, dataset_id, name, **kwargs):
    title = kwargs.get('title')
    description = kwargs.get('description')

    field_properties = Field_Properties.query.filter_by(project_id=project_id,
        dataset_id=dataset_id,
        name=name).one()

    for k, v in kwargs.iteritems():
        setattr(field_properties, k, v)

    db.session.commit()
    return row_to_dict(field_properties)


def update_field_properties_type_by_id(project_id, field_id, field_type, general_type):
    field_properties = Field_Properties.query.filter_by(
        id=field_id,
        project_id=project_id,
        ).one()

    field_properties.type = field_type
    field_properties.general_type = general_type
    field_properties.manual = True

    db.session.commit()
    return row_to_dict(field_properties)


################
# Relationships
################
def insert_relationships(relationships, project_id):
    relationship_objects = []
    for r in relationships:
        relationship_objects.append(Relationship(
            project_id = project_id,
            **r
        ))
    db.session.add_all(relationship_objects)
    db.session.commit()
    return [ row_to_dict(r) for r in relationship_objects ]


################
# Specifications
################
def get_spec(spec_id, project_id, **kwargs):
    spec = Spec.query.filter_by(id=spec_id, project_id=project_id, **kwargs).one()
    if spec is None:
        abort(404)
    exported_spec_ids = [ es.id for es in spec.exported_specs.all() ]
    if exported_spec_ids:
        exported = True
    else:
        exported = False
    setattr(spec, 'exported', exported)
    setattr(spec, 'exported_spec_ids', exported_spec_ids)
    return row_to_dict(spec, custom_fields=[ 'exported', 'exported_spec_ids'])

def get_specs(project_id, dataset_id, **kwargs):
    specs = Spec.query.filter_by(project_id=project_id, dataset_id=dataset_id, **kwargs).all()
    if specs is None:
        abort(404)
    final_specs = []
    for spec in specs:
        exported_spec_ids = [ es.id for es in spec.exported_specs.all() ]
        if exported_spec_ids:
            exported = True
        else:
            exported = False
        setattr(spec, 'exported', exported)
        setattr(spec, 'exported_spec_ids', exported_spec_ids)
    return [ row_to_dict(s, custom_fields=[ 'exported', 'exported_spec_ids' ]) for s in specs ]


from time import time
def insert_specs(project_id, specs, selected_fields, recommendation_types, conditionals, config):
    start_time = time()
    spec_objects = []
    for s in specs:
        spec_object = Spec(
            project_id = project_id,
            selected_fields = selected_fields,
            conditionals = conditionals,
            recommendation_types = recommendation_types,
            config = config,
            **s
        )
        setattr(spec_object, 'exported', False)
        setattr(spec_object, 'exported_spec_ids', [])
        spec_objects.append(spec_object)

    db.session.add_all(spec_objects)
    db.session.commit()
    logger.info('Insertion took %s seconds', (time() - start_time))
    return [ row_to_dict(s, custom_fields=[ 'exported', 'exported_spec_ids' ]) for s in spec_objects ]

def delete_spec(project_id, exported_spec_id):
    # TODO Accept multiple IDs
    try:
        spec = Spec.query.filter_by(project_id=project_id, id=exported_spec_id).one()
    except NoResultFound, e:
        return None
    except MultipleResultsFound, e:
        raise e
    db.session.delete(spec)
    db.session.commit()
    return row_to_dict(spec)

################
# Exported Specifications
################
def get_public_exported_spec(exported_spec_id, spec_type):
    print spec_type, ContentType.VISUALIZATION.value
    try:
        if spec_type == ContentType.VISUALIZATION.value:
            exported_spec = Exported_Spec.query.filter_by(
                id=exported_spec_id
            ).one()
            desired_spec_keys = [ 'generating_procedure', 'type_structure', 'viz_types', 'meta', 'dataset_id' ]
            for desired_spec_key in desired_spec_keys:
                value = getattr(exported_spec.spec, desired_spec_key)
                setattr(exported_spec, desired_spec_key, value)
            return row_to_dict(exported_spec, custom_fields=desired_spec_keys)

        elif spec_type == ContentType.CORRELATION.value:
            exported_spec = Exported_Correlation.query.filter_by(
                id=exported_spec_id
            ).one()
            return row_to_dict(exported_spec)

        elif spec_type == ContentType.REGRESSION.value:
            exported_spec = Exported_Regression.query.filter_by(
                id=exported_spec_id
            ).one()
            return row_to_dict(exported_spec)
    except NoResultFound, e:
        return None
    except MultipleResultsFound, e:
        raise e

def get_exported_spec(project_id, exported_spec_id):
    try:
        spec = Exported_Spec.query.filter_by(
            id=exported_spec_id,
            project_id=project_id
        ).one()
        return row_to_dict(spec)
    except NoResultFound, e:
        return None
    except MultipleResultsFound, e:
        raise e

def get_exported_spec_by_fields(project_id, spec_id, **kwargs):
    try:
        spec = Exported_Spec.query.filter_by(
            spec_id = spec_id,
            project_id = project_id,
            **kwargs
        ).one()
        return row_to_dict(spec)
    except NoResultFound, e:
        return None
    except MultipleResultsFound, e:
        raise e

def get_exported_specs(project_id):
    exported_specs = Exported_Spec.\
        query.\
        filter_by(project_id=project_id).\
        all()

    desired_spec_keys = [ 'generating_procedure', 'type_structure', 'viz_types', 'meta', 'dataset_id' ]

    final_specs = []
    for exported_spec in exported_specs:
        final_spec = exported_spec
        for desired_spec_key in desired_spec_keys:
            value = getattr(final_spec.spec, desired_spec_key)
            setattr(final_spec, desired_spec_key, value)
        final_specs.append(final_spec)
    return [ row_to_dict(final_spec, custom_fields=desired_spec_keys) for final_spec in final_specs ]

def insert_exported_spec(project_id, spec_id, data, conditionals, config):
    exported_spec = Exported_Spec(
        project_id = project_id,
        spec_id = spec_id,
        data = data,
        conditionals = conditionals,
        config = config
    )

    db.session.add(exported_spec)
    db.session.commit()

    spec = Spec.query.filter_by(id=spec_id, project_id=project_id).one()
    if spec is None:
        abort(404)

    desired_spec_keys = [ 'generating_procedure', 'type_structure', 'viz_types', 'meta', 'dataset_id' ]
    for desired_spec_key in desired_spec_keys:
        value = getattr(spec, desired_spec_key)
        setattr(exported_spec, desired_spec_key, value)

    return row_to_dict(exported_spec, custom_fields=desired_spec_keys)

def delete_exported_spec(project_id, exported_spec_id):
    exported_spec = Exported_Spec.query.filter_by(project_id=project_id, id=exported_spec_id).one()

    if exported_spec is None:
        abort(404)

    db.session.delete(exported_spec)
    db.session.commit()
    return row_to_dict(exported_spec)


################
# Analyses
################
def get_regression_by_id(regression_id, project_id):
    regression = Regression.query.filter_by(id=regression_id, project_id=project_id).one()
    if regression is None:
        abort(404)
    return row_to_dict(regression)


def get_regression_from_spec(project_id, spec):
    try:
        regression = Regression.query.filter_by(project_id=project_id, spec=spec).one()
    except NoResultFound:
        return None
    return row_to_dict(regression)


def insert_regression(project_id, spec, data):
    regression = Regression(
        project_id = project_id,
        spec = spec,
        data = data
    )
    db.session.add(regression)
    db.session.commit()
    return row_to_dict(regression)

def delete_regression(project_id, regression_id):
    try:
        regression = Regression.query.filter_by(project_id=project_id, id=regression_id).one()
    except NoResultFound, e:
        return None
    except MultipleResultsFound, e:
        raise e
    db.session.delete(regression)
    db.session.commit()
    return row_to_dict(regression)

def get_correlation_by_id(correlation_id, project_id):
    correlation = Correlation.query.filter_by(id=correlation_id, project_id=project_id).one()
    if correlation is None:
        abort(404)
    return row_to_dict(correlation)


def get_correlation_from_spec(project_id, spec):
    try:
        correlation = Correlation.query.filter_by(project_id=project_id, spec=spec).one()
    except NoResultFound:
        return None
    return row_to_dict(correlation)


def insert_correlation(project_id, spec, data):
    correlation = Correlation(
        project_id = project_id,
        spec = spec,
        data = data
    )
    db.session.add(correlation)
    db.session.commit()
    return row_to_dict(correlation)

def delete_correlation(project_id, correlation_id):
    try:
        correlation = Correlation.query.filter_by(project_id=project_id, id=correlation_id).one()
    except NoResultFound, e:
        return None
    except MultipleResultsFound, e:
        raise e
    db.session.delete(correlation)
    db.session.commit()
    return row_to_dict(correlation)

################
# Summaries
################
def get_summary_by_id(summary_id, project_id):
    summary = Summary.query.filter_by(id=summary_id, project_id=project_id).one()
    if summary is None:
        abort(404)
    return row_to_dict(summary)


def get_summary_from_spec(project_id, spec):
    try:
        summary = Summary.query.filter_by(project_id=project_id, spec=spec).one()
    except NoResultFound:
        return None
    return row_to_dict(summary)


def insert_summary(project_id, spec, data):
    summary = Summary(
        project_id = project_id,
        spec = spec,
        data = data
    )
    db.session.add(summary)
    db.session.commit()
    return row_to_dict(summary)

def delete_summary(project_id, summary_id):
    try:
        summary = Summary.query.filter_by(project_id=project_id, id=summary_id).one()
    except NoResultFound, e:
        return None
    except MultipleResultsFound, e:
        raise e
    db.session.delete(summary)
    db.session.commit()
    return row_to_dict(summary)

################
# Exported Analyses
################

# Regressions
def get_exported_regression_by_id(project_id, exported_regression_id):
    try:
        exported_regression = Exported_Regression.query.filter_by(id=exported_regression_id,
            project_id=project_id).one()
    except NoResultFound, e:
        return None
    except MultipleResultsFound, e:
        raise e
    return row_to_dict(exported_regression)

def get_exported_regression_by_regression_id(project_id, regression_id):
    try:
        exported_regression = Exported_Regression.query.filter_by(regression_id=regression_id,
            project_id=project_id).one()
    except NoResultFound, e:
        return None
    except MultipleResultsFound, e:
        raise e
    return row_to_dict(exported_regression)

def get_exported_regressions(project_id):
    exported_regressions = Exported_Regression.query.filter_by(project_id=project_id).all()
    for e in exported_regressions:
        setattr(e, 'spec', e.regression.spec)
        setattr(e, 'type', 'regression')
    return [ row_to_dict(exported_regression, custom_fields=['type', 'spec']) for exported_regression in exported_regressions ]

def insert_exported_regression(project_id, regression_id, data, conditionals, config):
    exported_regression = Exported_Regression(
        project_id = project_id,
        regression_id = regression_id,
        data = data,
        conditionals = conditionals,
        config = config
    )
    db.session.add(exported_regression)
    db.session.commit()
    return row_to_dict(exported_regression)

def delete_exported_regression(project_id, exported_regression_id):
    try:
        exported_regression = Exported_Regression.query.filter_by(project_id=project_id, id=exported_regression_id).one()
    except NoResultFound, e:
        return None
    except MultipleResultsFound, e:
        raise e

    db.session.delete(exported_regression)
    db.session.commit()
    return row_to_dict(exported_regression)

###################
# Interaction Terms
###################

def insert_interaction_term(project_id, dataset_id, variables):
    interaction_term = Interaction_Term(
        project_id=project_id,
        dataset_id=dataset_id,
        variables=variables
    )
    db.session.add(interaction_term)
    db.session.commit()
    return row_to_dict(interaction_term)

def get_interaction_term_by_project_id(project_id):
    try:
        interaction_term = Interaction_Term.query.filter_by(project_id=project_id)
    except NoResultFound, e:
        return None
    except MultipleResultsFound, e:
        raise e
    print interaction_term
    return row_to_dict(interaction_term)

def get_interaction_term_by_dataset_id(dataset_id):
    try:
        interaction_term = Interaction_Term.query.filter_by(dataset_id=dataset_id)
    except NoResultFound, e:
        return None
    except MultipleResultsFound, e:
        raise e
    print interaction_term
    return row_to_dict(interaction_term)    

def delete_interaction_term(interaction_term_id):
    try:
        interaction_term = Interaction_Term.query.filter_by(id=interaction_term_id).one()
    except NoResultFound, e:
        return None
    except MultipleResultsFound, e:
        raise e

    db.session.delete(interaction_term)
    db.commit()
    return row_to_dict(interaction_term)

##############
# Correlations
##############

def get_exported_correlation_by_id(project_id, exported_correlation_id):
    try:
        exported_correlation = Exported_Correlation.query.filter_by(id=exported_correlation_id,
            project_id=project_id).one()
    except NoResultFound, e:
        return None
    except MultipleResultsFound, e:
        raise e
    return row_to_dict(exported_correlation)

def get_exported_correlation_by_correlation_id(project_id, correlation_id):
    try:
        exported_correlation = Exported_Correlation.query.filter_by(correlation_id=correlation_id,
            project_id=project_id).one()
    except NoResultFound, e:
        return None
    except MultipleResultsFound, e:
        raise e
    return row_to_dict(exported_correlation)

def get_exported_correlations(project_id):
    exported_correlations = Exported_Correlation.query.filter_by(project_id=project_id).all()
    for e in exported_correlations:
        setattr(e, 'spec', e.correlation.spec)
        setattr(e, 'type', 'correlation')
    return [ row_to_dict(exported_correlation, custom_fields=['type', 'spec']) for exported_correlation in exported_correlations ]

def insert_exported_correlation(project_id, correlation_id, data, conditionals, config):
    exported_correlation = Exported_Correlation(
        project_id = project_id,
        correlation_id = correlation_id,
        data = data,
        conditionals = conditionals,
        config = config
    )
    db.session.add(exported_correlation)
    db.session.commit()
    return row_to_dict(exported_correlation)

def delete_exported_correlation(project_id, exported_correlation_id):
    try:
        exported_correlation = Exported_Correlation.query.filter_by(project_id=project_id, id=exported_correlation_id).one()
    except NoResultFound, e:
        return None
    except MultipleResultsFound, e:
        raise e

    db.session.delete(exported_correlation)
    db.session.commit()
    return row_to_dict(exported_correlation)


# Summary
def get_exported_summary_by_id(project_id, exported_summary_id):
    exported_summary = Exported_Summary.query.filter_by(id=exported_summary_id,
        project_id=project_id).one()
    if exported_summary is None:
        abort(404)
    return row_to_dict(exported_summary)

def get_exported_summarys(project_id):
    exported_summarys = Exported_Summary.query.filter_by(project_id=project_id).all()
    for e in exported_summarys:
        setattr(e, 'spec', e.summary.spec)
        setattr(e, 'type', 'summary')
    return [ row_to_dict(exported_summary, custom_fields=['type', 'spec']) for exported_summary in exported_summarys ]

def insert_exported_summary(project_id, summary_id, data, conditionals, config):
    exported_summary = Exported_Summary(
        project_id = project_id,
        summary_id = summary_id,
        data = data,
        conditionals = conditionals,
        config = config
    )
    db.session.add(exported_summary)
    db.session.commit()
    return row_to_dict(exported_summary)

def delete_exported_summary(project_id, exported_summary_id):
    try:
        exported_summary = Exported_Summary.query.filter_by(project_id=project_id, id=exported_summary_id).one()
    except NoResultFound, e:
        return None
    except MultipleResultsFound, e:
        raise e

    db.session.delete(exported_summary)
    db.session.commit()
    return row_to_dict(exported_summary)

################
# Documents
################
def get_documents(project_id):
    documents = Document.query.filter_by(project_id=project_id).all()
    if documents is None:
        abort(404)
    return [ row_to_dict(d) for d in documents ]

def get_public_document(document_id):
    try:
        document = Document.query.filter_by(id=document_id).one()
        return row_to_dict(document)
    except NoResultFound, e:
        logger.error(e)
        return None
    except MultipleResultsFound, e:
        logger.error(e)
        raise e

def get_document(project_id, document_id):
    try:
        document = Document.query.filter_by(project_id=project_id, id=document_id).one()
        return row_to_dict(document)
    except NoResultFound, e:
        logger.error(e)
        return None
    except MultipleResultsFound, e:
        logger.error(e)
        raise e

def create_document(project_id, title='Unnamed Document', content={ 'blocks': [] }):
    document = Document(
        project_id=project_id,
        title=title,
        content=content
    )
    db.session.add(document)
    db.session.commit()
    return row_to_dict(document)

def update_document(project_id, document_id, title, content):
    document = Document.query.filter_by(project_id=project_id, id=document_id).one()
    document.content = content
    document.title = title
    db.session.add(document)
    db.session.commit()
    return row_to_dict(document)

def delete_document(project_id, document_id):
    document = Document.query.filter_by(project_id=project_id, id=document_id).one()
    db.session.delete(document)
    db.session.commit()
    return row_to_dict(document)
