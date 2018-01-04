# -*- coding: utf-8 -*-
<%inherit file="visualization_base.mako"/>

## No stylesheets
## Default stylesheets
<%def name="stylesheets()">
    ${h.css('base')}
    ${h.css('bootstrap-tour')}
</%def>

## No javascript libraries
<%def name="late_javascripts()">
    <% tag_attrs = ' '.join([ '{0}="{1}"'.format( key, attr ) for key, attr in script_tag_attributes.items() ]) %>
    <script type="text/javascript">
        ## global configuration object
        ## TODO: remove
        window.Galaxy = window.Galaxy || {};
        window.Galaxy.root = '${h.url_for( "/" )}';
        window.Galaxy.config = {};
    </script>
    ${h.js( 'libs/jquery/jquery',
            'libs/jquery/jquery-ui',
            'libs/jquery/select2',
            'libs/bootstrap',
            'libs/underscore',
            'libs/backbone',
            'libs/d3',
            'libs/require',
            'bundled/libs.bundled',
            'bundled/chart.bundled')}
    <script type="text/javascript">
        ## global configuration object
        ## TODO: remove
        window.Galaxy = window.Galaxy || {};
        window.Galaxy.root = '${h.url_for( "/" )}';
        window.Galaxy.config = {};


        // configure require for base
        // due to our using both script tags and require, we need to access the same jq in both for plugin retention
        // source http://www.manuel-strehl.de/dev/load_jquery_before_requirejs.en.html
        window.jQuery = window.jquery = window.$;
        define( 'jquery', [], function(){ return window.$; })
        // TODO: use one system

        // shims and paths
        require.config({
            baseUrl: "${h.url_for('/static/scripts') }",
            shim: {
                "libs/underscore": {
                    exports: "_"
                },
                "libs/backbone": {
                    deps: [ 'jquery', 'libs/underscore' ],
                    exports: "Backbone"
                }
            },
            // cache busting using time server was restarted
            urlArgs: 'v=${app.server_starttime}'
        });
        $(function() {
            var config = ${ h.dumps( config ) };
            var app = bundleEntries.chart({
                visualization_id : ${ h.dumps( visualization_id ) } || undefined,
                dataset_id       : config.dataset_id,
                chart_dict       : config.chart_dict,
                id               : 'c9a973ea7f36d114'
            });
            $( 'body' ).append( app.$el );
        });
    </script>
</%def>