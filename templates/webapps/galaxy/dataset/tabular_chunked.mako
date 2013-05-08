<%inherit file="/base.mako"/>
<%namespace file="/dataset/display.mako" import="render_deleted_data_message" />

<%def name="title()">Dataset Display</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js( "libs/require" )}
    ${h.templates("helpers-common-templates")}

    <script type="text/javascript">
        require.config({ 
            baseUrl: "${h.url_for('/static/scripts')}",
            shim: {
                "libs/backbone/backbone": { exports: "Backbone" },
                "libs/backbone/backbone-relational": ["libs/backbone/backbone"]
            }
        });

        require(['mvc/data'], function(data) {
            data.createTabularDatasetChunkedView(
                _.extend( ${h.to_json_string( trans.security.encode_dict_ids( dataset.get_api_value() ) )}, 
                        {
                            url_viz: "${h.url_for( controller='/visualization')}",
                            chunk_url: "${h.url_for( controller='/dataset', action='display',
                                             dataset_id=trans.security.encode_id( dataset.id ))}",
                            first_data_chunk: ${chunk}
                        } 
                ),
                // Append view to body.
                $('body')
            );
        });
    </script>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
</%def>

${ render_deleted_data_message( dataset ) }