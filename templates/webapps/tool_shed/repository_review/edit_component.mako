<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Change component description</div>
    <div class="toolFormBody">
        <form name="edit_component" action="${h.url_for( controller='repository_review', action='edit_component' )}" method="post" >
            <div class="form-row">
                <label>Name:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    ${component.name | h}
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Description:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input  name="description" type="textfield" value="${component.description | h}" size=40"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="hidden" name="id" value="${trans.security.encode_id( component.id )}"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <input type="submit" name="edit_component_button" value="Save"/>
            </div>
        </form>
    </div>
</div>
