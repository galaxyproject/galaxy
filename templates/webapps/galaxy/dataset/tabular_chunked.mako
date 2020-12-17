<%inherit file="/base.mako"/>
<%namespace file="/dataset/display.mako" import="render_deleted_data_message" />

<%def name="title()">Dataset Display</%def>

<%def name="javascript_app()">

    <!-- tabular_chunked.mako javascript_app() -->
    ${parent.javascript_app()}

    <script type="text/javascript">
    %if dataset.datatype.file_ext != 'ipynb':
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

    %elif dataset.datatype.file_ext == 'ipynb':
            config.addInitialization(function() {
                console.log("display.mako", "chunkable init");

                var target = $('body');
                var item = ${h.dumps(dataset.to_dict())};

                $(target).children().remove();
                window.bundleEntries.createJupyterNotebookView({
                    id: item.id,
                    parent_elt: target
                });
            })
    %endif
    </script>
    
</%def>

${ render_deleted_data_message( dataset ) }
