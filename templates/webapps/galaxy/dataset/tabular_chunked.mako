<%inherit file="/base.mako"/>
<%namespace file="/dataset/display.mako" import="render_deleted_data_message" />

<%def name="title()">Dataset Display</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js("bundled/extended.bundled")}

    <script type="text/javascript">
        $(function(){
            bundleEntries.createTabularDatasetChunkedView({
                dataset_config : _.extend( ${ h.dumps( trans.security.encode_dict_ids( dataset.to_dict() ) )}, {
                        first_data_chunk: ${ chunk }
                    }),
                parent_elt : $( 'body' )
            });
        });
    </script>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
</%def>

${ render_deleted_data_message( dataset ) }
