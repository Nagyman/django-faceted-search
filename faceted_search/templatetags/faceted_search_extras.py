import logging
from django.template import Library
from django.contrib.admin.templatetags.admin_list import result_list
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.conf import settings
register = Library()

logger = logging.getLogger(__name__)

def get_facets(facet_list, facet_field=None, sort_by=None):
    facets = {'facets':facet_list}
    if facet_field:
        facet = facet_list.get(facet_field, None)
        if facet:
            if sort_by == 'value':
                facet.sort_by_value()
            elif sort_by == 'count':
                facet.sort_by_count()
            facets['facets'] = [facet]
        else:
            logger.warning('Facet field not found %s' % facet_field)
            return {'facets':None}

    return facets
                     
@register.inclusion_tag("faceted_search/facets.html")
def show_facets(facet_list, facet_field=None, sort_by=None):
    return get_facets(facet_list, facet_field, sort_by)

@register.inclusion_tag("faceted_search/facets_select.html")
def show_facets_as_select(facet_list, facet_field=None, sort_by=None):
    return get_facets(facet_list, facet_field, sort_by)

@register.inclusion_tag("faceted_search/facets_dl.html")
def show_facets_as_dl(facet_list, facet_field=None, sort_by=None):
    return get_facets(facet_list, facet_field, sort_by)
    
@register.inclusion_tag("faceted_search/date_facets.html")
def show_date_facets(facets, facet_field=None):
    return show_facets(facets, facet_field=facet_field, sort_by='value')

@register.inclusion_tag("faceted_search/price_facets.html", takes_context=True)
def show_price_facets(context, facet_list, facet_field=None, sort_by=None):
    '''
    A widget for showing price range selection in faceted search
    '''
    tag_context = show_facets(facet_list, facet_field, sort_by)
    
    tag_context.update({
        'currency': context['currency'],
        'slider_max': settings.PRICE_FACET_MAX,
        'price_field': ''.join((settings.PRICE_FACET_ROOT,'_',context['currency'].code,)),
    })

    return tag_context

@register.inclusion_tag("faceted_search/facet_counts.html")
def show_facet_items(facet):
    return { 'facet': facet }

@register.simple_tag
def facet_item_url(facet_item):
    # Deprecated
    return '?%s' % (facet_item.url_param(),)
