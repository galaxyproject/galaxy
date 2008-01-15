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
            Sucesfully ran workflow "${workflow.name}", the following datasets have
            been added to the queue.
        </p>
    
        <div style="padding-left: 10px;">
            %for step_outputs in outputs.itervalues():
                %for data in step_outputs.itervalues():
                    <p><b>${data.hid}</b>: ${data.name}</p>
                %endfor
            %endfor
        </div>
    </div>
</body>
    
</html>