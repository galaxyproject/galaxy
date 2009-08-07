<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/library/common.mako" import="render_template_info" />

<br/><br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='library', action='browse_library', id=library.id )}"><span>Browse this library</span></a>
    </li>
</ul>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

%if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY, library_item=library ):
    <div class="toolForm">
        <div class="toolFormTitle">Change library name and description</div>
        <div class="toolFormBody">
            <form name="library" action="${h.url_for( controller='library', action='library', rename=True )}" method="post" >
                <div class="form-row">
                    <label>Name:</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="text" name="name" value="${library.name}" size="40"/>
                    </div>
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <label>Description:</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="text" name="description" value="${library.description}" size="40"/>
                    </div>
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="hidden" name="id" value="${library.id}"/>
                    </div>
                    <div style="clear: both"></div>
                </div>
                <input type="submit" name="rename_library_button" value="Save"/>
            </form>
        </div>
    </div>
    <p/>
%else:
    <div class="toolForm">
        <div class="toolFormTitle">View information about ${library.name}</div>
        <div class="toolFormBody">
            <div class="form-row">
                <b>Name:</b> ${library.name}
                <div style="clear: both"></div>
                <b>Description:</b> ${library.description}
                <div style="clear: both"></div>
            </div>
        </div>
    </div>
%endif

%if widgets:
    ${render_template_info( library, library.id, widgets )}
%endif
