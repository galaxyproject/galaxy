<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">

<head>
<link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />
<script>
if ( parent.frames && parent.frames.galaxy_history ) {
    parent.frames.galaxy_history.location.href="${h.url_for( controller='root', action='history' ) }";
}
</script>
</head>

<body>
    <div class="donemessage">
        <p>
            Successfully ran workflow "${workflow.name}", the following datasets have
            been added to the queue.
            %if new_history:
                These datasets will appear in a new history:
                <a target='galaxy_history' href="${h.url_for( controller='history', action='list', operation="Switch", id=trans.security.encode_id(new_history.id), use_panels=False, show_deleted=False )}">
                    '${h.to_unicode(new_history.name)}'.
                </a>
            %endif
        </p>
        <div style="padding-left: 10px;">
            %for step_outputs in outputs.itervalues():
                %for data in step_outputs.itervalues():
                    %if not new_history or data.history == new_history:
                        <p><b>${data.hid}</b>: ${data.name}</p>
                    %endif
                %endfor
            %endfor
        </div>
    </div>
</body>
    
</html>
