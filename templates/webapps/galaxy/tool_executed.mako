<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>

<head>
<title>Galaxy</title>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />
<script type="text/javascript">
  var inside_galaxy_frameset = false;

  if ( parent.frames && parent.frames.galaxy_history ) {
      parent.frames.galaxy_history.location.href="${h.url_for( controller='root', action='history' )}";
      inside_galaxy_frameset = true;
  }

  %if trans.user:  
      if (inside_galaxy_frameset)
      {
            //parent.frames.galaxy_tools.update_recently_used();
      }
  %endif
  
  if ( parent.handle_minwidth_hint ) {
      parent.handle_minwidth_hint( -1 );
  }

  function main() {
    // If called from outside the galaxy frameset, redirect there
    %if tool.options.refresh:
      if ( ! inside_galaxy_frameset ) {
        setTimeout( "refresh()", 1000 );
        document.getElementById( "refresh_message" ).style.display = "block";
      }
    %endif
  }

  function refresh() {
    top.location.href = '${h.url_for( "/" )}';
  }  

</script>

</head>

<body onLoad="main()">

<div class="donemessagelarge">

<p>The following job has been successfully added to the queue:</p>

%for data in out_data.values():
   <div style="padding: 10px"><b> ${data.hid}: ${data.name}</b></div>
%endfor

<p>
You can check the status of queued jobs and view the resulting 
data by refreshing the <b>History</b> pane. When the job has been run
the status will change from 'running' to 'finished' if completed 
successfully or 'error' if problems were encountered.
</p>

%if tool.options.refresh:
<p id="refresh_message" style="display: none;">You are now being redirected back to <a href="${h.url_for( '/' )}">Galaxy</a></div>
%endif

</div>

</body>

</html>
