# -*- coding: utf-8 -*-
import factory
import logging
from collections import OrderedDict
from faceted_search.facets import FacetList, Facet, FacetItem

logger = logging.getLogger(__name__)

class FacetListFactory(factory.Factory):
    FACTORY_FOR = FacetList

    @classmethod
    def _prepare(cls, create, **kwargs):
        with_auto_facets = kwargs.pop('with_auto_facets', False)  # auto-create facets
        number_of_facets = kwargs.pop('number_of_facets', 1) # number of facets to auto-create 
        unselected_items = kwargs.pop('unselected_items', 1) # number of unselected items in each facet to auto-create
        selected_items = kwargs.pop('selected_items', 1) # number of selected items in each facet to auto-create
        fixed_item_value = kwargs.pop('fixed_item_value', None) # set all auto-created items to a fixed value
        with_selected_facets = kwargs.pop('with_selected_facets',{})
        with_unselected_facets = kwargs.pop('with_unselected_facets', {})

        facet_list = super(FacetListFactory, cls)._prepare(create, **kwargs)

        custom_facets = OrderedDict(with_selected_facets.items() + with_unselected_facets.items())
        for field, item_value in custom_facets.iteritems():
            facet = FacetFactory.build(field=field)
            facet_item = FacetItemFactory.build(value=item_value, is_selected=field in with_selected_facets)
            facet_item.facet = facet
            facet.items.append(facet_item)
            facet_list.append(facet)

        if with_auto_facets:
            for f in range(number_of_facets):
                facet = FacetFactory.build()
                for si in range(selected_items):
                    facet_item = FacetItemFactory.build(is_selected=True)
                    if fixed_item_value:
                        facet_item.value = fixed_item_value
                    facet_item.facet = facet
                    facet.items.append(facet_item)

                for ui in range(unselected_items):
                    facet_item = FacetItemFactory.build()
                    if fixed_item_value:
                        facet_item.value = fixed_item_value
                    facet_item.facet = facet
                    facet.items.append(facet_item)

                facet_list.append(facet)

        return facet_list

class FacetFactory(factory.Factory):
    FACTORY_FOR = Facet

    field = factory.Sequence(lambda n: 'facet_{}'.format(n))
    label = factory.Sequence(lambda n: 'Facet {}'.format(n))

    @classmethod
    def _prepare(cls, create, **kwargs):
        item_list = kwargs.pop('item_list',[])

        facet = super(FacetFactory, cls)._prepare(create, **kwargs)
        if(item_list):
            facet.items = item_list

        return facet

class FacetItemFactory(factory.Factory):
    FACTORY_FOR = FacetItem

    value = factory.Sequence(lambda n: '[0 TO {}]'.format(n))
    label = factory.Sequence(lambda n: 'FacetItem {}'.format(n))
    is_selected = False
    count = 0
