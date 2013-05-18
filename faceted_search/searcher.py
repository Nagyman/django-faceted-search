import re
import logging
from cgi import parse_qs
from urllib import urlencode
from datetime import datetime, timedelta

from django.utils import datetime_safe
from django.contrib.sites.models import Site

from haystack.query import SearchQuerySet
from haystack import connections

from faceted_search.utils import DATETIME_REGEX, check_parse_date, humanize_range
from faceted_search.facets import Facet, QueryFacet, FacetList, FacetItem

SORT_PARAM = 'order_by'
KEYWORD_PARAM = 'q'

'''
If a keyword is supplied, often we don't want to perform any ordering
so that the results are shown by relevance (score). Setting this value
to False causes the default sort order to be omitted if there is a keyword
supplied with the search. This does not apply if sort order is explicitly set.
'''
USE_DEFAULT_SORT_WITH_KEYWORD = False

logger = logging.getLogger(__name__)

class SearcherError(Exception): pass


class Searcher(object):
    '''
    A generic class for searching any indexed model.

    TODO:
        * find a different way to configure facet behaviour, perhaps directly in the index class??? e.g. meta?
    '''     

    def __init__(self, model=None, facets={}, sort_config={}):
        self.model = model
        self.queryset = None
        self.field_facets = facets.get('fields', {})
        self.date_facets = facets.get('dates', {})
        self.query_facets = facets.get('queries', {})
        self.facets = FacetList()
        self.indexed_fields = connections['default'].get_unified_index().all_searchfields()
        self.sort_config = sort_config

    def search(self, filters=None, keywords=None, order_by='', **kwargs):
        '''
        filters
            the field-value which all results must match
        keywords
            plain search string for matching text
        order_by
            the sort order of the results (a field name)
        '''
        logger.debug("Searching with filters %s" % filters)
        self.filters = filters or {}
        self.cleaned_filters = self._clean_filters(self.filters)
        self.queryset = SearchQuerySet()
        self.use_default_order = not order_by
        self.order_by = self.clean_sort_order(order_by)
        self.keywords = keywords or self.filters.get(KEYWORD_PARAM, '')
        if self.keywords and not USE_DEFAULT_SORT_WITH_KEYWORD and self.use_default_order:
            self.order_by = ''
        self.queryset = self.queryset.models(self.model).filter(**kwargs)
        self._narrow_queryset(self.cleaned_filters)
        self._keyword_filtered()
        self._field_faceted()
        self._query_faceted()
        self._date_faceted()
        self._ordered()
        self.facets = self._facets()
        self.search_performed = True
        return self.queryset
 
    @property
    def default_sort_order(self):
        for conf in self.sort_config:
            if conf.get('default', False):
                return conf.get('field') if not conf.get('reverse', False) else '-%s'% conf.get('field')
        return None

    def clean_sort_order(self, sort_order):
        '''
        Ensures the sort_order exists in the sort_config, otherwise
        returns the default_sort_order.
        '''
        config = self.get_sort_order_config(sort_order)
        if config:
            return sort_order
        return self.default_sort_order
   
    def get_sort_order_config(self, sort_order):
        '''
        Helper to get the config of a specific sort order
        '''
        if not sort_order:
            return {}
        is_reverse = sort_order.startswith('-')
        field = sort_order[1:] if is_reverse else sort_order
        for conf in self.sort_config:
            if conf['field'] == field and conf.get('reverse', False) == is_reverse:
                return conf
        logger.warning('No sort_order config found for %s' % sort_order)
        return {}

    def url_param(self):
        '''
        Construct the URL parameters from the last search performed. This
        is a combination of facet parameters, keywords, and sorting. This
        does not include the question mark, only the '&' joined key-values.
        '''
        if not self.search_performed:
            raise SearcherError('No search has been performed')

        return self.facets.url_param()

    def _clean_filters(self, filters):
        '''
        Helper to ensure only indexed fields are filtered
        '''
        cleaned = {}
        for key, value in filters.items():
            if key in self.indexed_fields and value:
                cleaned[key] = value

        return cleaned

    def _facets(self):
        '''
        Fetch and parse facet counts.
        '''
        facet_counts = self.queryset.facet_counts()
        facets = self._parse_field_facets(facet_counts.get('fields', {}))
        facets = facets + self._parse_query_facets(facet_counts.get('queries', {}))
        facets = facets + self._parse_date_facets(facet_counts.get('dates', {}))
        
        extra_params = {}
        if self.keywords:
            extra_params[KEYWORD_PARAM] = self.keywords
        if self.order_by and not self.use_default_order:
            extra_params[SORT_PARAM] = self.order_by

        facet_list = FacetList(extra_params=extra_params)
        for facet in facets:
            facet_list.append(facet)
        return facet_list

    @property
    def sort_options(self):
        '''
        A list of sort option dicts
        (
            {'url':'...', 'label': 'A name', 'selected':True}
        )
        '''
        opts = []
        use_default = not self.order_by

        # Remove any existing sort order parameters that may have been
        # included as extra_params to the FacetList. This prevents multiple
        # sort orders from being included in the sort urls.
        query = parse_qs(self.facets.url_param())
        query.pop(SORT_PARAM, None) 
        query = dict((k, v[0]) for k, v in query.iteritems())

        for conf in self.sort_config:
            reverse = conf.get('reverse', False)
            field = conf.get('field') if not reverse else '-%s'% conf.get('field')
            is_default = conf.get('default', False)
            if not is_default:
                sort_query = {SORT_PARAM: field}
                sort_query.update(query)
                url = '?%s' % urlencode(sort_query)
            else:
                url = '?%s' % urlencode(query)

            opts.append({
                'url': url,
                'label': conf.get('label'),
                'selected': (use_default and is_default) or (self.order_by == field),
            })
        return opts

    def _ordered(self):
        if not self.order_by:
            return
        self.queryset = self.queryset.order_by(self.order_by)
                                           
    def _keyword_filtered(self):
        if self.keywords:
            self.queryset = self.queryset.filter(text=self.queryset.query.clean(self.keywords))

    def _field_faceted(self):
        '''
        See search_indexes.py for the defined faceted fields.
        '''
        for field, config in self.field_facets.iteritems():
            self.queryset = self.queryset.facet(field)

    def _query_faceted(self):
        for field, queries in self.query_facets.iteritems():
            for query in queries:
                self.queryset = self.queryset.query_facet(field, query)

    def _date_faceted(self):
        for field, config in self.date_facets.iteritems():
            self.queryset = self.queryset.date_facet(field, 
                        start_date=config['start_date'],
                        end_date=config['end_date'],
                        gap_by=config['gap_by'])

    def _parse_date_facets(self, facet_items):
        '''
        Parse date faceted fields like:
            {'departure_dates': {'2010-04-24T18:17:03Z': 105,
                               '2010-05-01T00:00:00Z': 323,
                               '2010-06-01T00:00:00Z': 334,
                               '2010-07-01T00:00:00Z': 468,
                               '2010-08-01T00:00:00Z': 504,
                               '2010-09-01T00:00:00Z': 515,
                               '2010-10-01T00:00:00Z': 519,
                               '2010-11-01T00:00:00Z': 478,
                               '2010-12-01T00:00:00Z': 457,
                               '2011-01-01T00:00:00Z': 370,
                               '2011-02-01T00:00:00Z': 357,
                               '2011-03-01T00:00:00Z': 370,
                               '2011-04-01T00:00:00Z': 359,
                               'end': '2011-05-01T00:00:00Z',
                               'gap': '+1MONTH/MONTH'}}
        '''
        facets = []
        for field, date_counts in facet_items.iteritems():
            facet = Facet(field=field, label=field.replace('_', ' ').title())
            gap = date_counts['gap']
            for date_string, count in date_counts.iteritems():
                match = DATETIME_REGEX.search(date_string)
                if not match: continue
                data = match.groupdict()
                date = datetime_safe.date(int(data['year']), int(data['month']), int(data['day']))
                item = FacetItem(date, count)
                if gap == '+1MONTH/MONTH':
                    item.label=date.strftime("%B")
                    item.value=date.strftime("%Y-%m")
                elif gap == '+1YEAR/YEAR':
                    item.label=date.strftime("%Y")
                    item.value=date.strftime("%Y-01") 
                item.is_selected = self._is_selected_facet(field, check_parse_date(item.value))
                item.facet = facet
                facet.items.append(item)
            facet.items.sort(key=lambda x: x.value)
            facets.append(facet)
        return facets

    def _parse_query_facets(self, facet_items):
        '''
        Parses query facet counts like this:
            {
                'min_price_USD_exact:[2001 TO *]': 306, 
                'duration_exact:[16 TO 25]': 149, 
                'min_price_USD_exact:[500 TO 1000]': 195, 
                'duration_exact:[41 TO *]': 35, 
                'duration_exact:[26 TO 40]': 52, 
                'min_price_USD_exact:[0 TO 500]': 88, 
                'duration_exact:[6 TO 10]': 329, 
                'min_price_USD_exact:[1001 TO 2000]': 292, 
                'duration_exact:[11 TO 15]': 256, 
                'duration_exact:[* TO 5]': 205
            }

        Returns a list of Facet objects (one per parsed field name).
        '''
        facets = {}
        for field_query, count in facet_items.iteritems():
            field, sep, query = field_query.partition(':')
            field = field.replace('_exact', '')
            if field in facets:
                facet = facets[field]
            else:
                facet = QueryFacet(field=field, label=field.replace('_', ' ').title())
                facets[field] = facet       
            item = FacetItem(query, count, label=humanize_range(query))
            item.is_selected = self._is_selected_facet(field, item.value)
            item.facet = facet
            facet.items.append(item)
        return [facet for field,facet in facets.iteritems()]    

    def _parse_field_facets(self, facet_items):
        '''
        Parses field facet counts like this:
            {'region': [('South America', 222),
                       ('Asia', 134),
                       ('Antarctica', 10),
                       ('South Pacific', 2)],
             'service_level': [('Standard', 351),
                              ('Basic', 202),
                              ('Comfort', 93),
                              ('Superior', 25)],}
        '''
        facets = []
        for field, counts in facet_items.iteritems():
            conf = self.field_facets[field]
            label = conf.get('label', field.replace('_', ' ').title())
            facet = Facet(field=field, label=label)
            for count in counts:
                item = FacetItem(count[0], count[1])
                item.is_selected = self._is_selected_facet(field, item.value)
                item.facet = facet
                facet.items.append(item)
            facets.append(facet)       
        return facets

    def _is_selected_facet(self, field, facet_value):
        '''
        Checks the existing narrow_queries to check if a given field:value
        exists, and is thus selected. Be careful not to modify facet_value
        as it would be reflected in the facet.
        '''
        for narrow in self.queryset.query.narrow_queries:
            value = self._solr_escape_value(facet_value)
            if narrow.partition(':') == (field, ':', value) or \
               narrow.partition(':') == ('%s_exact'%field, ':', value):
                return True
        return False
     
    def _narrow_queryset(self, filters):
        '''
        Helper to narrow a queryset using a dict of key-value pairs
        '''
        if not filters: return

        for field, value in filters.iteritems():
            # Generally, django-haystack will use the correct _exact field
            # for filtering on facets, but for custom query facets it doesn't
            # so we just make sure that the _exact field is used.
            value = check_parse_date(value)
            value = self._solr_escape_value(value)
            field = '%s_exact' % field if self.indexed_fields[field].faceted else field
            self.queryset = self.queryset.narrow('%(field)s:%(value)s' % { 'field':field, 'value':value})
                                    
    def _solr_escape_value(self, value):
        '''
        Escape Solr special characters
        '''
        # ranges shouldn't have spaces escaped
        if '[' in value: return value

        ESCAPE_CHARS_RE = re.compile(r'(?<!\\)(?P<char>[&|+\-!(){}[\]^ "~*?:])')

        escaped = ESCAPE_CHARS_RE.sub(r'\\\g<char>', value)

        return escaped
