<%inherit file="/base.mako"/>
    
%if message:
<%
if messagetype is UNDEFINED:
    mt = "done"
else:
    mt = messagetype
%>
<p />
<div class="${mt}message">
    ${message}
</div>
<p />
%endif

<div class="toolForm">
    <div class="toolFormTitle">Rename workflow '${stored.name}'</div>
        <div class="toolFormBody">
            <form action="${h.url_for(controller='workflow', action='rename', id=trans.security.encode_id(stored.id) )}" method="POST">
                <div class="form-row">
                    <label>
                        New name
                    </label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="text" name="new_name" value="${stored.name}" size="40">
                    </div>
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <input type="submit" value="Rename"></input>
                </div>
            </form>
        </div>
    </div>
</div>
