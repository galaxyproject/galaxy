<%def name="render_sample_datasets( sample )">
    ${len( sample.datasets )} / ${len( sample.transferred_dataset_files )}
</%def>

${render_sample_datasets( sample )}
