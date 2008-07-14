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
    <div class="toolFormTitle">Share workflow '${stored.name}'</div>
        <div class="toolFormBody">
            <form action="${h.url_for( action='share', id=trans.security.encode_id(stored.id) )}" method="POST">
                <div class="form-row">
                    <label>
                        Email address of user to share with
                    </label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="text" name="email" value="${email}" size="40">
                    </div>
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <input type="submit" value="Share"></input>
                </div>
            </form>
        </div>
    </div>
</div>