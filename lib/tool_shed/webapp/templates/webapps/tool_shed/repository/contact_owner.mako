<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/tool_shed/common/repository_actions_menu.mako" import="render_tool_shed_repository_actions" />

<%!
   def inherit(context):
       if context.get('use_panels'):
           return '/webapps/tool_shed/base_panels.mako'
       else:
           return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

${render_tool_shed_repository_actions( repository, metadata=metadata )}

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Contact the owner of the repository named '${repository.name | h}'</div>
    <div class="toolFormBody">
        <div class="form-row">
            This feature is intended to streamline appropriate communication between
            Galaxy tool developers and those in the Galaxy community that use them.
            Please don't send messages unnecessarily.
        </div>
        <form name="send_to_owner" id="send_to_owner" action="${h.url_for( controller='repository', action='send_to_owner', id=trans.security.encode_id( repository.id ) )}" method="post" >
            <div class="form-row">
                <label>Message:</label>
                <textarea name="message" rows="10" cols="40"></textarea>
            </div>
            <div class="form-row">
                <input type="submit" value="Send to owner"/>
            </div>
        </form>
    </div>
</div>
