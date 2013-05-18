# -*- coding: utf-8 -*-
import logging
from urllib import urlencode
from collections import OrderedDict

from django.utils import unittest
from django.conf import settings

from currencies.tests import CurrencyFactory
from faceted_search.tests.factories import (
    FacetListFactory,
    FacetFactory,
    FacetItemFactory,
)
from faceted_search.facets import FacetList, Facet, QueryFacet, FacetItem

logger = logging.getLogger(__name__)

class FacetListTestCase(unittest.TestCase):
    def setUp(self):
        self.ITEM_VALUE = '[0 TO 500]'
        self.selected_facets = OrderedDict([
            ('min_price_GBP','[500 TO 1000]'),
            ('region','Africa'),
        ])
        self.facet_list = FacetListFactory.build(
                    with_auto_facets=True,
                    number_of_facets=2,
                    selected_items=0,
                    unselected_items=2,
                    with_selected_facets=self.selected_facets,
                    with_unselected_facets={
                        'duration': '[6 TO 10]',
                        'country': 'Austria',
                    },
        )

    def test_creates_url_params_from_selected_items(self):
        # should build a url out of the selected FacetItems
        self.assertEqual(
            self.facet_list.url_param(),
            urlencode(self.selected_facets),
        )

        # should exclude a selected FacetItem if we tell it to
        self.assertEqual(
            self.facet_list.url_param(
                facet_item=self.facet_list.facets[0].items[0],
                include_facet_item=False,
            ),
            urlencode(OrderedDict(self.selected_facets.items()[1:]))
        )

        # Should not include a FacetItem if it has been excluded at the list level
        self.facet_list.exclude_params.append('min_price_GBP')
        self.assertEqual(
            self.facet_list.url_param(facet_item=self.facet_list.facets[0].items[0]),
            urlencode(OrderedDict(self.selected_facets.items()[1:]))
        )

        # Should include a non-selected FacetItem we pass in if we tell it to
        # Note the exclude from the previous test is still active
        facet = FacetFactory.build(field='foreign_facet')
        facet_item = FacetItemFactory.build(value='[500 TO 1000]')
        facet_item.facet = facet
        self.assertEqual(
            self.facet_list.url_param(facet_item=facet_item),
            urlencode(OrderedDict([
                (self.facet_list.facets[1].field, self.facet_list.facets[1].items[0].value),
                (facet.field, facet_item.value),
            ]))
        )

        # Should exclude a non-selected FacetItem if it is in the ecxlude list
        self.facet_list.exclude_params.append(facet.field)
        self.assertEqual(
            self.facet_list.url_param(facet_item=facet_item),
            urlencode({self.facet_list.facets[1].field: self.facet_list.facets[1].items[0].value})
        )

class FacetTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def test_localizes_field(self):
        base_field_name = 'min_price'
        self.assertEqual(Facet.localize_field(
                base_field_name = base_field_name,
                currency_code = 'CAD',
        ), 'min_price_CAD')
        self.assertEqual(Facet.localize_field(
                base_field_name = base_field_name,
                currency_code = 'gbp',
        ), 'min_price_GBP')
        self.assertEqual(Facet.localize_field(
                base_field_name = base_field_name,
        ), 'min_price_%s' % settings.DEFAULT_CURRENCY_CODE)

class QueryFacetTestCase(unittest.TestCase):
    def setUp(self):
        self.duration_range = '[6 TO 10]'
        self.price_range = '[0 TO *]'
        self.date_range = '[2010-12-01T00:00:00Z TO 2010-12-31T00:00:00Z]'

    def test_validates_ranges(self):
        self.assertTrue(QueryFacet.validate_range(self.duration_range))
        self.assertTrue(QueryFacet.validate_range(self.price_range))
        self.assertTrue(QueryFacet.validate_range(self.date_range))
        self.assertFalse(QueryFacet.validate_range('I Am Not A Range'))

class FacetItemTestCase(unittest.TestCase):
    def setUp(self):
        self.duration_query = '[6 TO 10]'
        self.price_query = '[500 TO 1000]'
        self.price_query_wildcard = '[0 TO *]'
        self.date_query = '2012-12-01-2012-12-15'

    def test_creates_label_from_query(self):
        self.assertEqual(
                FacetItem.label_from_query(self.duration_query),
                '6 to 10'
        )

    def test_creates_price_label_from_query(self):
        currency = CurrencyFactory.build(
                code='GBP',
                html_symbol='&pound;'
        )
        self.assertEqual(
                FacetItem.price_label_from_query(self.price_query),
                '$500 to 1000'
        )
        self.assertEqual(
                FacetItem.price_label_from_query(self.price_query_wildcard),
                '$0 to %s' % str(settings.PRICE_FACET_MAX)
        )
        self.assertEqual(
                FacetItem.price_label_from_query(self.price_query, currency),
                '&pound;500 to 1000'
        )

    def test_creates_date_label_from_query(self):
        self.assertEqual(
                FacetItem.date_label_from_query(self.date_query),
                'Dec  1, 2012 to Dec 15, 2012'
        )
        self.assertEqual(
                FacetItem.date_label_from_query('This Is Not A Range'),
                'This Is Not A Range'
        )

    def test_builds_url(self):
        base_url = '/trips'
        selected_facets = OrderedDict([
            ('min_price_GBP','[500 TO 1000]'),
            ('region','Africa'),
        ])
        facet_list = FacetListFactory.build(
            with_selected_facets=selected_facets
        )

        facet_item = facet_list.facets[0].items[0]
        self.assertEqual(
                facet_item._build_url(),
                ''.join(('?', urlencode(selected_facets),))
        )

        self.assertEqual(
                facet_item._build_url(include_self=False),
                ''.join(('?',urlencode(OrderedDict(selected_facets.items()[1:])),))
        )

        facet_item.base_url = base_url
        self.assertEqual(
                facet_item._build_url(),
                ''.join((base_url, '?', urlencode(selected_facets),))
        )


