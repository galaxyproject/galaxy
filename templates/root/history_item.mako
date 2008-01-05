<%namespace file="history_common.mako" import="render_dataset" />

## this is necessary because this dataset remains in history.active_datasets
## after deletion, until the history is reloaded
## FIXME: still necessary now that we don't re-pull finished datasets?  test.
%if data.deleted is not True:
    ${render_dataset( data, hid )}    
%endif