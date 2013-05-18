import re
import logging

from collections import OrderedDict
from urllib import urlencode
from django.conf import settings
from django.utils.safestring import mark_safe

from currencies.models import Currency
from faceted_search.utils import is_valid_date_range, parse_date_range
                      
logger = logging.getLogger(__name__)

FACET_SORT_ORDER = getattr(settings, 'FACET_SORT_ORDER', [])
 
class FacetList(object):
    '''
    Hybrid List/Dict of Facets. Facets can be looked up
    by field name O(n)
    '''
    def __init__(self, extra_params=None, exclude_params=None):
        '''
        extra_params
            (key-values) to be added to the url_param
            for this facet list. This is useful for example, retaining
            sort order, or other non-facet query parameters such as keywords.
        exclude_params
            parameters to exclude when calling url_param. Used for ommiting
            implicit parameters from facet URLs
        '''
        self.facets = []
        self.extra_params = extra_params or {}
        self.exclude_params = exclude_params or []

    def append(self, facet):
        facet.facet_set = self
        self.facets.append(facet)

    def remove(self, facet):
        self.facets.remove(facet)

    def selected_facet_items(self):
        items = []
        for f in self.facets:
            items = items + f.selected_items()
        # Sort the selected facets by the search_settings.FACETS_ALL list index
        if FACET_SORT_ORDER:
            return sorted(items, key=lambda f: FACET_SORT_ORDER.index(f.facet.field) if f.facet.field in FACET_SORT_ORDER else 0)
        else:
            return items
    
    def has_selected(self):
        '''
        True if any of the facets have selected items
        '''
        return any(f.has_selected() for f in self.facets)

    def has_active(self):
        '''
        True if there are any facets have potential to be selected
        '''
        return any(f.has_active() for f in self.facets)   
 
    def url_param(self, facet_item=None, include_facet_item=True):
        '''
        Return a url parameter for the given facet item which
        may be used to filter current results.
        '''
        param = OrderedDict()
        if self.extra_params:
            param = self.extra_params.copy()
        
        for item in self.selected_facet_items():
            if item == facet_item and not include_facet_item:
                # Our facet item could be selected so exclude it if we are told to
                continue

            if item.facet.field not in self.exclude_params:
                param.update({item.facet.field: item.value})

        # This is to capture a facet_item that may not be part of our selected items
        if isinstance(facet_item, FacetItem) and include_facet_item and facet_item.facet.field not in self.exclude_params:
            param.update({facet_item.facet.field: facet_item.value})

        return urlencode(OrderedDict([k, v.encode('utf-8')] for k, v in param.items()))
                      
    def get(self, key, default='__NOT_SET__'):
        if default == '__NOT_SET__':
            return self[key]
        else:
            try:
                return self[key]
            except KeyError:
                return default

    def __getitem__(self, key):
        for facet in self.facets:
            if facet.field == key:
                return facet
        raise KeyError(key)

    def __setitem__(self, key, value):
        item = self[key]
        self.facets.remove(item)
        self.facets.append(value)

    def __len__(self):
        return len(self.facets)
    
    def __iter__(self):
        return iter(self.facets)

    def __contains__(self, item):
        try:
            if self[item]:
                return True
        except KeyError:
            return False
        except:
            raise
        
        return False

class Facet(object):
    '''
    Represents a term on which querysets can be filtered (faceted) 
    Relates to a set of FacetItems representing the individual values 
    that can be selected for this Facet.

    `field`
        Used for URL parameters and matches the field name in the search index
    `label`
        Front-end label displayed on the page
    '''
    def __init__(self, field, label, label_plural=None):
        self.field = field
        self.label = mark_safe(label)
        self.label_plural = label_plural or self._pluralize(field)
        self.items = []
        self.facet_set = None

    @staticmethod
    def localize_field(base_field_name, currency_code=settings.DEFAULT_CURRENCY_CODE):
        '''
        Generate an l10n facet field name based on currency code and a base
        '''
        return ''.join((base_field_name, '_', currency_code.upper()))

    def _pluralize(self, value):
        '''
        Primative pluralization util, used for pluralizing the label
        '''
        if not value:
            return value

        last_char = value[-1]
        if last_char == 's':
            return '%ses' % value 
        elif last_char == 'y':
            return '%sies' % value[:-1]
        else:
            return '%ss' % value       
            

    def sort_by_value(self):
        self.items = sorted(self.items, key=lambda item: item.value)

    def sort_by_count(self):
        self.items = sorted(self.items, key=lambda item: item.count, reverse=True)

    def has_selected(self):
        '''
        Returns true if any facet items in this facet are selected
        '''
        return any(i.is_selected for i in self.items)

    def has_active(self):
        '''
        Return true if there are more than one facet items with a count greater
        than one. This is used to hide facets that don't have many sensible options
        available to the user.
        '''
        return len([i for i in self.items if i.count > 1 and not i.is_selected]) > 0

    def selected_items(self):
        return [i for i in self.items if i.is_selected]

    def remove(self, item):
        self.items.remove(item)
 
    def __len__(self):
        return len(self.items)             
 
    def __iter__(self):
        return iter(self.items)
 
    def __getitem__(self, key):
        for item in self.items:
            if item.value == key:
                return item
        raise KeyError(key)
                   
    def get(self, key, default='__NOT_SET__'):
        try:
            return self[key]
        except KeyError:
            if default == '__NOT_SET__':
                return None
            return default

    def __str__(self):
        return 'Facet: {} ({})'.format(self.field,len(self.items))

    def __unicode__(self):
        return self.__str__()

class QueryFacet(Facet):
    '''
    This class is generally just for overriding that method to sort values properly.
    The Facet.sort_by_value screws up the ordering of query based facets,
    which have values that look like:
        [* TO 500], '[500 TO 1000], '[1001 TO 2000], [2001 TO *], etc.

    '''
    @staticmethod
    def validate_range(value):
        '''
        Determine if the value describes a valid range query
        '''
        return bool(re.compile("\[.* TO .*\]").match(value))

    def sort_by_value(self):
        self.items = sorted(self.items, key=lambda item: self._sort_val(item.value))

    def _sort_val(self, val):
        '''Returns the numeric value of a query facet for sorting'''
        sort_val = val.lstrip('[').rstrip(']').split()[0].replace('*', '0') 
        return int(sort_val)

class FacetItem(object):
    '''
    A user selectable criteria within a Facet. Contains helper methods
    for generating the full URL to add the criteria to the existing
    query.
    '''
    def __init__(self, value, count, label=None, 
                       is_selected=False, base_url=''):
        self.value = value
        self.label = mark_safe(label) if label else value
        self.count = count
        self.is_selected = is_selected
        self.facet = None
        self.base_url = base_url

        # Date facets might need grouping in the templates
        self.year = getattr(value, 'year', None)
 
    @property
    def url(self):
        return self._build_url()

    @property
    def removal_url(self):
        '''
        Generate a url that can be used to remove the facet (ie from the
        breadcrumb)
        '''
        return self._build_url(include_self=False)

    @staticmethod
    def label_from_query(query_value):
        return query_value.replace('[', '').replace(']', '').lower()

    @staticmethod
    def price_label_from_query(query_value, currency=None):
        if not isinstance(currency, Currency):
            currency = Currency.objects.get(code=settings.DEFAULT_CURRENCY_CODE)

        label = FacetItem.label_from_query(query_value).replace('*', str(settings.PRICE_FACET_MAX))

        return ''.join((currency.symbol(),label,))

    @staticmethod
    def date_label_from_query(query_value):
        DATE_DISPLAY_FORMAT = '%b %e, %Y'

        date_range = parse_date_range(query_value)
        if date_range:
            return "%s to %s" % (date_range[0].strftime(DATE_DISPLAY_FORMAT), date_range[1].strftime(DATE_DISPLAY_FORMAT))

        return query_value

    def is_range(self):
        '''
        Determine if the FacetItem describes a range query
        '''
        return QueryFacet.validate_range(self.value)

    def url_param(self, include_self=True):
        '''
        Builds a url parameter which will turn on/off
        the respective facet_item while maintaining existing
        selected filters. This is what provides the drill down/up
        urls when displaying facet links. Full construction takes
        place in the facet_set which 'knows' the other facet states.
        This must be manually appended to the desired base url
        including whichever named parameter it will be extracted from.

        e.g. '/some/path?filter=%s' % facet_item.url_param()
        '''

        return self.facet.facet_set.url_param(facet_item=self,include_facet_item=include_self)

    def _build_url(self, include_self=True):
        url_pieces = (self.base_url, self.url_param(include_self))

        if '?' in self.base_url:
            if '&' in self.base_url:
                return '%s&%s' % url_pieces 
            return '%s%s' % url_pieces 
        return '%s?%s' % url_pieces   

    def __unicode__(self):
        return 'FacetItem: %s (%d)' % (self.label, self.count)

    def __str__(self):
        return self.__unicode__()
         
