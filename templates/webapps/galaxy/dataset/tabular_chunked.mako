<%inherit file="/base.mako"/>
<%namespace file="/dataset/display.mako" import="render_deleted_data_message" />

<%def name="title()">Dataset Display</%def>

<%def name="javascript_app()">

    <!-- tabular_chunked.mako javascript_app() -->
    ${parent.javascript_app()}

    <script type="text/javascript">
        config.addInitialization(function(galaxy) {
            var dataset = ${ h.dumps( trans.security.encode_dict_ids( dataset.to_dict() ) )};
            var firstChunk = ${chunk};
            window.bundleEntries.createTabularDatasetChunkedView({
                dataset_config : Object.assign(dataset, {
                    first_data_chunk: firstChunk
                }),
                parent_elt : $('body')
            });
        });
    </script>
    
</%def>

${ render_deleted_data_message( dataset ) }
