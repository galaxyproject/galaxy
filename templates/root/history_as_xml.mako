<?xml version="1.0"?>
<history>
    %if show_deleted:
        %for data in history.activatable_datasets:
            <data id="${data.id}" hid="${data.hid}" name="${data.name}" state="${data.state}" dbkey="${data.dbkey}">
                ${_(data.blurb)}
            </data>
        %endfor
    %else:
        %for data in history.active_datasets:
            <data id="${data.id}" hid="${data.hid}" name="${data.name}" state="${data.state}" dbkey="${data.dbkey}">
                ${_(data.blurb)}
            </data>
        %endfor
    %endif
</history>
