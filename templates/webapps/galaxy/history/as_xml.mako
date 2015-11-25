<?xml version="1.0"?>
<history id="${trans.security.encode_id( history.id )}" num="${len(history.datasets)}" name="${history.name}" create="${history.create_time}" update="${history.update_time}">
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
