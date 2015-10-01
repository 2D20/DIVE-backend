from enum import Enum


class DataType(Enum):

    # Fundamental
    INTEGER = 'integer'
    STRING = 'string'
    DECIMAL = 'decimal'
    BOOLEAN = 'boolean'

    # Special strings
    TEXT = 'text'
    URL = 'url'

    # Geographic
    LATITUDE = 'latitude'
    LONGITUDE = 'longitude'
    CITY = 'city'
    COUNTRY_CODE_2 = 'countryCode2'
    COUNTRY_CODE_3 = 'countryCode3'
    COUNTRY_NAME = 'countryName'
    CONTINENT_NAME = 'continentName'

    # Temporal
    DATETIME = 'datetime'
    DATE = 'date'
    TIME = 'time'
    YEAR = 'year'
    MONTH = 'month'
    DAY = 'day'


class DataTypeWeights(Enum):
    # Fundamental
    INTEGER = 6
    STRING = 1
    DECIMAL = 4
    BOOLEAN = 7

    # Special strings
    TEXT = 8
    URL = 8

    # Geographic
    LATITUDE = 10
    LONGITUDE = 10
    CITY = 10
    COUNTRY_CODE_2 = 10
    COUNTRY_CODE_3 = 10
    COUNTRY_NAME = 10
    CONTINENT_NAME = 10

    # Temporal
    DATETIME = 3
    DATE = 3
    TIME = 3
    YEAR = 10
    MONTH = 10
    DAY = 10


class PseudoType(Enum):
    LIST = 'list'

class FileType(Enum):
    CSV = 'csv'
    TSV = 'tsv'
    XLS = 'xls'
    XLSX = 'xlsx'
