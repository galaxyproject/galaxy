<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>

<head>
<title>Galaxy</title>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />
<script type="text/javascript">
  var inside_galaxy_frameset = false;

  // refresh the history panel to include any new datasets created by the tool
  if( top.Galaxy && top.Galaxy.currHistoryPanel ){
        top.Galaxy.currHistoryPanel.refreshContents();
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

%if num_jobs > 1:
  <% jobs_str = "%d jobs have" % num_jobs %>
%else:
  <% jobs_str = "A job has" %>
%endif
%if len(out_data) == 1:
  <% datasets_str = "dataset" %>
%else:
  <% datasets_str = "datasets" %>
%endif

<p>
  ${jobs_str} been successfully added to the queue - resulting in the following ${datasets_str}:
</p>
%for _, data in out_data:
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

%if job_errors:
<div class="errormessagelarge">
  There were errors setting up ${len(job_errors)} submitted job(s):
  <ul>
  <!-- Styling on this list is a little flat. Consider identing these error messages. -->
  %for job_error in job_errors:
    <li><b>${job_error}</b></li>
  %endfor
  </ul>
</div>
%endif

</body>

</html>
