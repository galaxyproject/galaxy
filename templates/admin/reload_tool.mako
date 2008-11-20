<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if msg:
    ${render_msg( msg, messagetype )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Reload Tool</div>
    <div class="toolFormBody">
    <form name="tool_reload" action="${h.url_for( controller='admin', action='tool_reload' )}" method="post" >
        <div class="form-row">
            <label>
                Tool to reload:
            </label>
            <select name="tool_id">
              %for i, section in enumerate( toolbox.sections ):
                <optgroup label="${section.name}">
                %for t in section.tools:
                  <option value="${t.id}">${t.name}</option>
                %endfor
              %endfor
            </select>
        </div>
        <div class="form-row">
            <button name="action" value="tool_reload">Reload</button>
        </div>
    </form>
    </div>
</div>
