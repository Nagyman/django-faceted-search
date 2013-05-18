import logging
import re
from datetime import datetime, timedelta
from django.conf import settings
import calendar

logger = logging.getLogger(__name__)

DATETIME_REGEX = re.compile('^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})(T|\s+)(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2}).*?$')
YEAR_MONTH_REGEX = re.compile('^(?P<year>\d{4})-(?P<month>\d{2})$')
DATE_RANGE_REGEX = re.compile('^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})-(?P<year2>\d{4})-(?P<month2>\d{2})-(?P<day2>\d{2})$')
EXACT_DATE_REGEX = re.compile('^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})$')
SOLR_RANGE = '[%s TO %s]'
SOLR_MONTH_RANGE_START = "%Y-%m-%dT00:00:00Z"
SOLR_MONTH_RANGE_END = "%Y-%m-%dT23:59:59Z"

def humanize_range(query):
    m = re.match(r'\[\* TO (\d*)\]', query)
    if m and m.groups(): return "Less than %s" % m.groups()
    m = re.match(r'\[(\d*) TO (\d*)\]', query)
    if m and m.groups(): return "%s to %s" % m.groups()
    m = re.match(r'\[(\d*) TO \*\]', query)
    if m and m.groups(): return "%s and up" % m.groups()
    return query
        
def check_parse_date(value):
    '''
    Dates in the url will not be passed in the solr range format,
    so this helper checks values for a date match and returns
    a correctly formatted date range for solr.

    [2010-12-01T00:00:00Z TO 2010-12-31T00:00:00Z]
    '''

    # Months are passed in the URL as YYYY-MM
    match = YEAR_MONTH_REGEX.match(value)
    if match:
        data = match.groupdict()
        year, month = (int(data['year']), int(data['month']))
        start_date = datetime(year, month, 1)
        end_date = datetime(year, month, calendar.monthrange(year, month)[1])  
        return SOLR_RANGE % (start_date.strftime(SOLR_MONTH_RANGE_START), end_date.strftime(SOLR_MONTH_RANGE_END))

    # Exact dates are passed in the URL as YYYY-MM-DD
    match = EXACT_DATE_REGEX.match(value)
    if match:
        data = match.groupdict()
        year, month, day = (int(data['year']), int(data['month']), int(data['day']))
        start_date = datetime(year, month, day)
        end_date = datetime(year, month, day)  
        return SOLR_RANGE % (start_date.strftime(SOLR_MONTH_RANGE_START), end_date.strftime(SOLR_MONTH_RANGE_END))

    # Date ranges are passed as YYYY-MM-DD-YYYY-MM-DD
    range = parse_date_range(value)
    if range:
        return SOLR_RANGE % (range[0].strftime(SOLR_MONTH_RANGE_START), range[1].strftime(SOLR_MONTH_RANGE_END))

    return value

def parse_date_range(date_range):
    match = is_valid_date_range(date_range)
    if match:
        data = match.groupdict()
        year, month, day = (int(data['year']), int(data['month']), int(data['day']))
        year2, month2, day2 = (int(data['year2']), int(data['month2']), int(data['day2']))
        start_date = datetime(year, month, day)
        end_date = datetime(year2, month2, day2)
        return (start_date, end_date)
    return None

def is_valid_date_range(date_range):
    return DATE_RANGE_REGEX.match(date_range)
