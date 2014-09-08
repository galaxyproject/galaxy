<%inherit file="/base.mako"/>
<%namespace file="/dataset/display.mako" import="render_deleted_data_message" />

<%def name="title()">Dataset Display</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js( "libs/require" )}

    <script type="text/javascript">
        require.config({
            baseUrl: "${h.url_for('/static/scripts')}",
            shim: {
                "libs/backbone/backbone": { exports: "Backbone" },
            }
        });

        require(['mvc/data'], function(data) {
            data.createTabularDatasetChunkedView({
                dataset_config: _.extend( ${h.dumps( trans.security.encode_dict_ids( dataset.to_dict() ) )}, 
                        {
                            first_data_chunk: ${chunk}
                        }
                ),
                parent_elt: $('body')
            });
        });
    </script>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
</%def>

${ render_deleted_data_message( dataset ) }
