import datetime
import os

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.solr_backend.SolrEngine',
        'URL': 'http://gapadventures-util0.gap.ca:8080/solr',
        'TIMEOUT': 60 * 5,
        'INCLUDE_SPELLING': False,
        'BATCH_SIZE': 30,
    }
}
 

# How many hours ago that a model's data was updated should be considered
# as new, and therefore reindexed.
HAYSTACK_UPDATE_AGE = 1 

#TODO Facet settings should be model specific.
FIELD_FACETS = {
    'region': {},
    'country': {},
    'trip_style': {},
    'service_level': {},
    'promotion_CAD': {'label': 'Promotions'},
    'promotion_USD': {'label': 'Promotions'},
    'promotion_NZD': {'label': 'Promotions'},
    'promotion_EUR': {'label': 'Promotions'},
    'promotion_USL': {'label': 'Promotions'},
    'promotion_GBP': {'label': 'Promotions'},
    'promotion_AUD': {'label': 'Promotions'},
    'promotion_CHF': {'label': 'Promotions'},
    'activity': {},
    'tag': {},
}

QUERY_FACETS = {
    'duration': ('[* TO 5]', '[6 TO 10]', '[11 TO 15]', '[16 TO 25]', '[26 TO 40]', '[41 TO *]'),
    'min_price_CAD': ('[0 TO 500]', '[500 TO 1000]', '[1001 TO 2000]', '[2001 TO *]'), 
    'min_price_USD': ('[0 TO 500]', '[500 TO 1000]', '[1001 TO 2000]', '[2001 TO *]'), 
    'min_price_NZD': ('[0 TO 500]', '[500 TO 1000]', '[1001 TO 2000]', '[2001 TO *]'), 
    'min_price_EUR': ('[0 TO 500]', '[500 TO 1000]', '[1001 TO 2000]', '[2001 TO *]'), 
    'min_price_USL': ('[0 TO 500]', '[500 TO 1000]', '[1001 TO 2000]', '[2001 TO *]'), 
    'min_price_GBP': ('[0 TO 500]', '[500 TO 1000]', '[1001 TO 2000]', '[2001 TO *]'), 
    'min_price_AUD': ('[0 TO 500]', '[500 TO 1000]', '[1001 TO 2000]', '[2001 TO *]'), 
    'min_price_CHF': ('[0 TO 500]', '[500 TO 1000]', '[1001 TO 2000]', '[2001 TO *]'), 
}

DATE_FACETS = {
    'departure_dates' : {
        'start_date': datetime.datetime.now(),
        'end_date': datetime.datetime.now()+datetime.timedelta(days=365),
        'gap_by': 'month',
    },

    'return_dates' : {
        'start_date': datetime.datetime.now(),
        'end_date': datetime.datetime.now()+datetime.timedelta(days=365),
        'gap_by': 'month',
    },
}

FACETS_DEFAULT = {'fields':FIELD_FACETS, 'queries': QUERY_FACETS, 'dates':DATE_FACETS}
                     
FACETS_ALL = [
    'min_price_CAD', 
    'min_price_USD'
    'min_price_NZD'
    'min_price_EUR'
    'min_price_USL'
    'min_price_GBP'
    'min_price_AUD'
    'min_price_CHF'
    'region', 
    'country', 
    'departure_dates', 
    'return_dates', 
    'duration', 
    'trip_style', 
    'service_level', 
    'promotion_CAD', 
    'promotion_USD'
    'promotion_NZD'
    'promotion_EUR'
    'promotion_USL'
    'promotion_GBP'
    'promotion_AUD'
    'promotion_CHF' 
    'activity',
    'tag',
]

FACET_BASE_URL_NAME = 'faceted_trips'

# Optinally defines the order in which selected facets are returned from
# FacetList.selected_facet_items(). This is an aid for having a known 
# order during iteration. Currently, it's used
# for controling the order of facet 'breadcrumbs'.
FACET_SORT_ORDER = FACETS_ALL

# Configure which fields can be sorted.
SORT_OPTIONS = (
    {'field':'priority', 'label':'Relevance', 'default':True},
    {'field':'byName', 'label': 'Trip Name (A-Z)', 'reverse':False},
    {'field':'byName', 'label': 'Trip Name (Z-A)', 'reverse':True},
    {'field':'duration', 'label': 'Duration (High to Low)', 'reverse':True},
    {'field':'duration', 'label': 'Duration (Low to High)', 'reverse':False},
    {'field':'min_price_CAD_exact', 'label':'Price (Low to High)'},
    {'field':'min_price_USD_exact', 'label':'Price (Low to High)'},
    {'field':'min_price_NZD_exact', 'label':'Price (Low to High)'},
    {'field':'min_price_EUR_exact', 'label':'Price (Low to High)'},
    {'field':'min_price_USL_exact', 'label':'Price (Low to High)'},
    {'field':'min_price_GBP_exact', 'label':'Price (Low to High)'},
    {'field':'min_price_AUD_exact', 'label':'Price (Low to High)'},
    {'field':'min_price_CHF_exact', 'label':'Price (Low to High)'}, 
    {'field':'min_price_CAD_exact', 'label':'Price (High to Low)', 'reverse':True},
    {'field':'min_price_USD_exact', 'label':'Price (High to Low)', 'reverse':True},
    {'field':'min_price_NZD_exact', 'label':'Price (High to Low)', 'reverse':True},
    {'field':'min_price_EUR_exact', 'label':'Price (High to Low)', 'reverse':True},
    {'field':'min_price_USL_exact', 'label':'Price (High to Low)', 'reverse':True},
    {'field':'min_price_GBP_exact', 'label':'Price (High to Low)', 'reverse':True},
    {'field':'min_price_AUD_exact', 'label':'Price (High to Low)', 'reverse':True},
    {'field':'min_price_CHF_exact', 'label':'Price (High to Low)', 'reverse':True},  
)
