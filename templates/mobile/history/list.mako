<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
         "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">

<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>Galaxy</title>
  <meta name="viewport" content="width=devicewidth; initial-scale=1.0; maximum-scale=1.0; user-scalable=0;"/>
  <meta name="apple-touch-fullscreen" content="YES" />
  <meta name="apple-mobile-web-app-capable" content="yes" />
  <style type="text/css" media="screen">@import "${h.url_for('/static/style/iphone.css')}";</style>
  <style>
    div.date {
        font-size: 13px;
        color: gray;
    }
    div.counts {
        padding-top: 1px;
        font-size: 13px;
        color: gray;
    }
  </style>
</head>

<body>
    <div class="toolbar masthead">
        <h1><img style="vertical-align: -5px;" src="${h.url_for("/static/images/galaxyIcon_noText.png")}"> Galaxy mobile</h1>
    </div>
    <div class="toolbar">
        
        <h1 id="pageTitle">Histories</h1>
        <a id="backButton" class="button" href="#"></a>
    </div>
    
    <ul selected="true">
            
            %for i, history in enumerate( trans.user.histories ):
    
                %if not ( history.purged or history.deleted ):
    
    
                        <li>
                            
                            <a href="${h.url_for( action="history_detail", id=history.id )}">
                                ${history.name}
                            
                            <div class="date">${h.date.distance_of_time_in_words( history.update_time, h.date.datetime.utcnow() )} ago</div>
              
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
</body>
