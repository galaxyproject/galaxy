<div id="history_detail_${history.id}">
    <div class="toolbar">
        <h1>${history.name}</h1>
        <a class="back button" href="#">Back</a>
    </div>
    <ul class="edgetoedge">
            
        %for data in history.active_datasets:
          %if data.visible:
              <%
                  hid = data.hid
                  if data.state in ['no state','',None]:
                      data_state = "queued"
                  else:
                      data_state = data.state
                      
                  if data_state == 'ok':
                    state_class = "dummy"
                  else:
                    state_class = data_state
              %>
            <li class="historyItemContainer state-color-${state_class}" id="historyItemContainer-${data.id}">
               
               <a href="${h.url_for( action="dataset_detail", id=data.id )}">
              
        <div>${hid}: ${data.display_name()}</div>
        
        <div class="secondary">
        ## Body for history items, extra info and actions, data "peek"
        
            %if not trans.app.security_agent.allow_action( trans.user, data.permitted_actions.DATASET_ACCESS, dataset = data.dataset ):
                <div>You do not have permission to view this dataset.</div>
            %elif data_state == "queued":
                <div>Job is waiting to run</div>
            %elif data_state == "running":
                <div>Job is currently running</div>
            %elif data_state == "error":
                <div>
                    An error occurred running this job.
                </div>
            %elif data_state == "discarded":
                <div>
                    The job creating this dataset was cancelled before completion.
                </div>
            %elif data_state == "empty":
                <div>No data: <i>${data.display_info()}</i></div>
            %elif data_state == "ok":
                <div>
                    ${data.blurb},
                    format: <span class="${data.ext}">${data.ext}</span>, 
                    database: <span class="${data.dbkey}">${data.dbkey}</span>
                </div>
	    %else:
		<div>Error: unknown dataset state "${data_state}".</div>
            %endif               
            </div>
        
          </a>
               
            </li>
        %endif 

        %endfor
              
    </ul>
</div>
