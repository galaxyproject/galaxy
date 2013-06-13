<div id="history_list">
    <div class="toolbar">
        <h1>Histories</h1>
        <a class="back button" href="#">Back</a>
    </div>
    
    %if trans.user is None:
    <ul class="edgetoedge">
      <li><i style="color: gray"> No histories available (not logged in) </i></li>
    </ul>
    
    %else:
    <ul class="edgetoedge">
            
            %for i, history in enumerate( trans.user.histories ):
    
                %if not ( history.purged or history.deleted ):
    
    
                        <li>
                            
                            <a href="${h.url_for(controller='mobile', action="history_detail", id=history.id )}">
                                ${history.name}
                            
                            <div class="secondary">${h.date.distance_of_time_in_words( history.update_time, h.date.datetime.utcnow() )} ago</div>
              
                            <div class="counts">
                            <%
                                total_ok = sum( 1 for d in history.active_datasets if d.state == 'ok' )
                                total_running = sum( 1 for d in history.active_datasets if d.state == 'running' )
                                total_queued = sum( 1 for d in history.active_datasets if d.state == 'queued' )
                                total_error = sum( 1 for d in history.active_datasets if d.state in ( 'error', 'fail' ) )
                                parts = []
                                if total_ok:
                                    parts.append( "<span style='color: #66AA66'>" + str(total_ok) + " finished</span>" )
                                if total_queued:
                                    parts.append( "<span style='color: #888888'>" + str(total_queued) + " queued</span>" )
                                if total_running:
                                    parts.append( "<span style='color: #AAAA66'>" + str(total_running) + " running</span>" )
                                if total_error:
                                    parts.append( "<span style='color: #AA6666'>" + str(total_error) + " failed</span>" )
                                
                            %>
                            ${", ".join( parts )}        
                            </div>
                            
                            </a>
              
                        </li>
                %endif
        %endfor
              
    </ul>
    %endif
</div>
