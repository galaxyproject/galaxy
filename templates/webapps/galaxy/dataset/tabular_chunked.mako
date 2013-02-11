<%inherit file="/base.mako"/>


<%def name="title()">Dataset Display</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js( "libs/require" )}
    <script type="text/javascript">
        require.config({ 
            baseUrl: "${h.url_for('/static/scripts')}",
            shim: {
                "libs/backbone/backbone": { exports: "Backbone" },
                "libs/backbone/backbone-relational": ["libs/backbone/backbone"]
            }
        });

        require(['mvc/data'], function(data) {

            // Set up dataset.
            var dataset = new data.TabularDataset( _.extend( ${h.to_json_string( dataset.get_api_value() )}, 
                {
                    chunk_url: "${h.url_for( controller='/dataset', action='display', 
                                             dataset_id=trans.security.encode_id( dataset.id ))}",
                    first_data_chunk: ${chunk}
                } 
            ) );
            
            // Set up, render, and add view.
            var dataset_view = new data.TabularDatasetChunkedView({
                model: dataset
            });
            dataset_view.render();
            $('body').append(dataset_view.$el);
        });
    </script>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
</%def>
