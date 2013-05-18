$(document).ready(function() {

    // NOTE: These are populated in price_facets.html
    // We should really do this via a configurable object
    //
    //var SLIDER_MIN = 0, SLIDER_MAX = {{ slider_max }};
    //var item_base_url = '{{ item.base_url }}';
    //var item_url = '{{ item.url|safe }}';
    //var item_count = '{{ item.count }}';
    //var price_field = '{{ price_field }}';
    //var price_query = '{{ item.value }}';
    var url_params = get_url_params(item_url.replace(item_base_url, ''));
    var price_values = parse_facet_query(price_query);
    var price_start = price_values ? price_values[0] : SLIDER_MIN
    var price_end = price_values ? price_values[1] : SLIDER_MAX;

    function get_url_params(query) {
        /*
         * Parse the query parameters from a query string or from
         * window.location.search if that hasn't been provided
         */
        var params = {};
        var match,
            pl     = /\+/g,  // Regex for replacing addition symbol with a space
            search = /([^&=]+)=?([^&]*)/g,
            decode = function (s) { return decodeURIComponent(s.replace(pl, " ")); };

        if(!query) {
            query = window.location.search;
        }

        query = query.substring(1);

        while (match = search.exec(query))
            params[decode(match[1])] = decode(match[2]);

        return params;
    }

    function parse_facet_query(facet_query) {
        /*
         * Parse a facet query in the form [n TO n]
         */
        if(Array.isArray(facet_query.match(/(\[\d+ TO \d+\])/gi))) {
            return facet_query.replace(/[\[\] ]+/g,'').split(/TO/i);
        }

        return null;
    }

    function get_min_price_label(start_range, end_range) {
        /*
         * Generate a label for the min_price facet based on a start
         * and end range
         */
        if(end_range == '*') {
            end_range = SLIDER_MAX;
        }
        if(end_range == SLIDER_MAX) {
            end_range += '+';
        }
        return currency_symbol + start_range + ' to ' + end_range;
    }

    function get_min_price_count_element() {
        /*
         * Return a basic element to contain the min_price facet count
         * results
         */
        return ' <span id="min_price_count"></span>';
    }

    function get_min_price_qs(start_range, end_range) {
        /*
         * Generate a query string for the min_price facet based on a
         * start and end range
         */
        var params = $.extend({}, url_params);

        if(end_range == SLIDER_MAX) {
            end_range = '*';
        }

        params[price_field] = '[' + start_range + ' TO ' + end_range + ']';

        return $.param(params);
    }

    $("#slider_min_price").slider({
        range: true,
        min: SLIDER_MIN,
        max: SLIDER_MAX,
        values: [price_start, price_end],
        slide: function(event, ui) {
            end_label = ui.values[1];
            if(ui.values[1] == SLIDER_MAX) {
                end_label = SLIDER_MAX + '+';
            }
            var min_price_count_html = $('#min_price_count').html();
            $('#min_price').html(get_min_price_label(ui.values[0], ui.values[1]));
            $('#min_price').append(get_min_price_count_element());
            $('#min_price_count').html(min_price_count_html);
        },
        change: function(event, ui) {

        },
        stop: function(event, ui) {
            $('#min_price').attr('href',item_base_url + '?' + get_min_price_qs(ui.values[0], ui.values[1]));
            /* Grab the search count for the new min_price query */
            $.ajax({
                dataType: "html",
                data: get_min_price_qs(ui.values[0], ui.values[1]) + '&count=true',
                success:function (data, code, xmlhttp) {
                    var count = parseInt(data, 10);
                    $('#min_price_count').html('(' + count + ')');
                }
            });
        }
    });

    /* Initialization */
    $('#min_price').html(get_min_price_label(price_start, price_end));
    $('#min_price').append(get_min_price_count_element());
    $('#min_price_count').html('(' + item_count + ')');
    $('#min_price').attr('href', item_url);
});   
