<%namespace file="/message.mako" import="render_msg" />

<%!
   def inherit(context):
       if context.get('use_panels'):
           return '/webapps/community/base_panels.mako'
       else:
           return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

<%def name="title()">View Tool</%def>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">${tool.name} <em>${tool.description}</em> ${tool.version} (ID: ${tool.tool_id})</div>
    <div class="toolFormBody">
    <div class="form-row">
        Uploaded by <a href="${h.url_for(controller='tool', action='user_tools')}">${tool.user.username}</a> on ${tool.create_time.strftime('%B %d, %Y')}
        <div style="clear: both"></div>
    </div>
    <div class="form-row">
        <label>Categories:</label>
        %for category in [ tca.category for tca in tool.categories ]:
            ${category.name}
        %endfor
        <div style="clear: both"></div>
    </div>
    <div class="form-row">
        <label>Description:</label>
        ${tool.user_description}
        <div style="clear: both"></div>
    </div>
    <div class="form-row">
        <label>Download:</label>
        <a href="${h.url_for(controller='tool', action='download_tool', id=trans.app.security.encode_id( tool.id ))}"><img src="${h.url_for('/static/images/silk/page_white_compressed.png')}"> ${tool.tool_id}_${tool.version}</a>
        <div style="clear: both"></div>
    </div>
    %if trans.user.id == tool.user_id:
        <div class="form-row">
            <em>This is your tool.  You may <a href="${h.url_for(controller='tool', action='edit_tool', id=trans.app.security.encode_id( tool.id ) )}">edit it</a>.</em>
            <div style="clear: both"></div>
        </div>
    %endif
    </div>
</div>
