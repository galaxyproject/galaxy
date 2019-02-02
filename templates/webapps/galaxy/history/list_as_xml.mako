<?xml version="1.0"?>
<history_ids>
  %for i, history in enumerate( t.user.histories ):
    <data id="${trans.security.encode_id( history.id )}" hid="${i+1}" num="${len(history.datasets)}" name="${history.name}" create="${history.create_time}" update="${history.update_time}" >
    </data>
  %endfor
</history_ids>
