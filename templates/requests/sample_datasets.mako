<%def name="render_sample_datasets( sample )">
    <a href="${h.url_for(controller='requests_admin', action='show_datatx_page', sample_id=trans.security.encode_id(sample.id))}">${sample.transferred_dataset_files()}/${len(sample.dataset_files)}</a>
</%def>



${render_sample_datasets( sample )}
