import datetime
from django.utils import datetime_safe
from haystack import indexes

from faceted_search.utils import DATETIME_REGEX
 
class MultiValueDateField(indexes.MultiValueField):
    '''
    Haystack does not currently have a MultiValueField that supports data types
    other than text (see: http://github.com/toastdriven/django-haystack/issues#issue/204)
    This class is mostly responsible for converting an indexed date from a string
    to a python date. Note that build_solr_schema will still create a multi valued text
    field which must be manually changed to the date type.
    '''
    def prepare(self, obj):
        return self.convert(super(MultiValueDateField, self).prepare(obj))
    
    def convert(self, value):
        if value is None:
            return None
     
        dates = []
        for list_value in value:
            if isinstance(list_value, basestring):
                match = DATETIME_REGEX.search(list_value)
                if match:
                    data = match.groupdict()
                    dates.append(datetime_safe.date(int(data['year']), int(data['month']), int(data['day'])))
                else:
                    raise SearchFieldError("Date provided to '%s' field doesn't appear to be a valid date string: '%s'" % (self.instance_name, list_value))
            elif isinstance(list_value, datetime.date):
                dates.append(list_value)
            else:
                raise SearchFieldError("Date provided to '%s' field doesn't appear to be a valid date: '%s'" % (self.instance_name, list_value))

        return list(dates)   
                         
