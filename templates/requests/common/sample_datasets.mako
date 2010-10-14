<%def name="render_sample_datasets( sample )">
    ${sample.transferred_dataset_files} / ${len( sample.datasets )}
</%def>

${render_sample_datasets( sample )}
