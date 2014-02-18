<div id="history_detail_${history.id}">
    <div class="toolbar">
        <h1>${history.name}</h1>
        <a class="back button" href="#">Back</a>
    </div>
    <ul class="edgetoedge">
            
        %for data in history.active_datasets:
            %if data.visible:

                <%
                    if data.state in ['no state','',None]:
                        data_state = "queued"
                    else:
                        data_state = str( data.state )
                %>

                <li id="historyItemContainer-${data.id}">
                
                    <div style="float: left; padding-right: 8px;">
                        <div style='display: none;' id="progress-${data.id}">
                            <img src="${h.url_for('/static/style/data_running.gif')}" border="0">
                        </div>
                        %if data_state == 'running':
                            <div><img src="${h.url_for('/static/style/data_running.gif')}" border="0"></div>
                        %elif data_state == 'upload':
                            <div><img src="${h.url_for('/static/style/data_upload.gif')}" border="0"></div>
                        %else:
                            <div><img src="${h.url_for( "/static/style/data_%s.png" % data_state )}" border="0"></div>
                        %endif
                    </div>    
           
                    <a href="${h.url_for(controller='mobile', action="dataset_detail", id=data.id )}">
              
                        <div>${data.hid}: ${data.display_name()}</div>
        
                        <div class="secondary">
                            ## Body for history items, extra info and actions, data "peek"
                            <% current_user_roles = trans.get_current_user_roles() %>
                            %if not trans.user_is_admin() and not trans.app.security_agent.can_access_dataset( current_user_roles, data.dataset ):
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
                            %elif data_state == 'setting_metadata':
                                <div>Metadata is being Auto-Detected.</div>
                            %elif data_state == "empty":
                                <div>No data: <i>${data.display_info()}</i></div>
                            %elif data_state in [ "ok", "failed_metadata" ]:
                                <div>
                                    %if data_state == "failed_metadata":
                                        Warning: setting metadata failed,
                                    %endif
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
