<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
         "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">

<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>Galaxy</title>
  <meta name="viewport" content="width=devicewidth; initial-scale=1.0; maximum-scale=1.0; user-scalable=0;"/>
  <meta name="apple-touch-fullscreen" content="YES" />
  <style type="text/css" media="screen">@import "${h.url_for('/static/style/iphone.css')}";</style>
  ## <script type="application/x-javascript" src="${h.url_for('/static/iui/iui.js')}"></script>
  <style>
    div.secondary {
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
        <h1 id="pageTitle">${history.name}</h1>
        <a id="backButton" class="button" href="${h.url_for( action='index', id=None )}" style="display: block;">Histories</a>
    </div>

    <ul selected="true">
            
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
</body>
