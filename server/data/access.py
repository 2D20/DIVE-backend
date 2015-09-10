'''
Functions for reading, sampling, and detecting types of datasets

No manipulation or calculation, only description
'''

import os
import re
import xlrd
import codecs
import pandas as pd

from flask import json
import csv


from . import DataType
from type_detection import get_column_types, detect_time_series

from config import config
from werkzeug.utils import secure_filename
from db import MongoInstance as MI

from bson.objectid import ObjectId
from in_memory_data import InMemoryData as IMD


# Return dataset
def get_dataset_structure(path):
    df = get_data(path=path)
    header = df.columns.values
    df = df.fillna('')
    n_rows, n_cols = df.shape
    types = get_column_types(df)
    time_series = detect_time_series(df)
    if time_series:
        structure = 'wide'
    else:
        structure = 'long'

    extension = path.rsplit('.', 1)[1]

    column_attrs = [{'name': header[i], 'type': types[i], 'column_id': i} for i in range(0, n_cols)]

    result = {
        'column_attrs': column_attrs,
        'header': list(header),
        'rows': n_rows,
        'cols': n_cols,
        'filetype': extension,
        'structure': structure,
        'time_series': time_series
    }

    return result

def get_dataset_data(path, start=0, inc=1000):
    end = start + inc  # Upper bound excluded
    df = get_data(path=path)
    df = df.fillna('')
    sample = map(list, df.iloc[start:end].values)

    result = get_dataset_structure(path)
    result['sample'] = sample
    return result


# Dataflow:
# 1. Save file in uploads/pID directory
# 2. Save file location in project data collection
# 3. Return sample
def upload_file(pID, file):
    full_file_name = secure_filename(file.filename)
    file_name, file_type = full_file_name.rsplit('.', 1)
    path = os.path.join(config['UPLOAD_FOLDER'], pID, full_file_name)

    datasets = []
    # Flat files
    if file_type in ['csv', 'tsv', 'txt'] :
        file.save(path)

        dID = MI.insertDataset(pID, path, full_file_name)
        data_doc = get_dataset_structure(path)
        data_doc.update({
            'title' : file_name,
            'filename' : full_file_name,
            'dID' : dID,
        })
        datasets.append(data_doc)

    # Excel files
    elif file_type.startswith('xls') :
        file.save(path)

        book = xlrd.open_workbook(path)
        sheet_names = book.sheet_names()

        for sheet_name in sheet_names:
            sheet = book.sheet_by_name(sheet_name)

            # Don't save empty sheets
            if sheet.nrows == 0:
                continue

            csv_file_name = file_name + "_" + sheet_name + ".csv"
            csv_path = os.path.join(config['UPLOAD_FOLDER'], pID, csv_file_name)

            csv_file = open(csv_path, 'wb')
            wr = csv.writer(csv_file, quoting=csv.QUOTE_ALL)
            for rn in xrange(sheet.nrows) :
                wr.writerow([ unicode(v).encode('utf-8') for v in sheet.row_values(rn) ])
            csv_file.close()

            dID = MI.insertDataset(pID, csv_path, csv_file_name)
            data_doc = get_dataset_structure(csv_path)
            data_doc.update({
                'title' : csv_file_name.rsplit('.', 1)[0],
                'filename' : csv_file_name,
                'dID' : dID
            })

            datasets.append(data_doc)

    elif file_type == 'json' :

        print "Saving file: ", filename
        file.save(path)
        print "Saved file: ", filename

        f = open(path, 'rU')
        json_data = json.load(f)

        path2 = path + ".csv"
        filename2 = filename + ".csv"

        csv_file = open(path2, 'wb')
        wr = csv.writer(csv_file, quoting=csv.QUOTE_ALL)

        header = json_data[0].keys()

        wr.writerow([v.encode('utf-8') for v in header])

        for i in range(len(json_data)) :
            row = []
            for field in header :
                row.append(json_data[i][field])
            wr.writerow([unicode(v).encode('utf-8') for v in row])
        csv_file.close()

        dID = MI.insertDataset(pID, path2, filename2)

        result = get_dataset_structure(path2)
        result.update({
            'title' : filename2.rsplit('.', 1)[0],
            'filename' : filename2,
            'dID' : dID,
        })
        datasets.append(result)
    return datasets


def get_data(pID=None, dID=None, path=None, nrows=None):
    if IMD.hasData(dID):
        return IMD.getData(dID)
    if path:
        delim = get_delimiter(path)
        df = pd.read_table(path, sep=delim, error_bad_lines=False, nrows=nrows)
    if dID:
        dataset = MI.getData({'_id' : ObjectId(dID)}, pID)[0]
        path = dataset['path']
        delim = get_delimiter(path)
        df = pd.read_table(path, sep=delim, error_bad_lines=False, nrows=nrows)
        IMD.insertData(dID, df)
    return df


# Utility function to detect extension and return delimiter
def get_delimiter(path):
    filename = path.rsplit('/')[-1]
    extension = filename.rsplit('.', 1)[1]
    if extension == 'csv':
        delim = ','
    elif extension == 'tsv':
        delim = '\t'
    # TODO Detect separators intelligently
    elif extension == 'txt':
        delim = ','
    return delim
