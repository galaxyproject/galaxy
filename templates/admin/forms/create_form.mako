<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif
<form name="create_form_definition" action="${h.url_for( controller='forms', action='create_form_definition' )}" enctype="multipart/form-data" method="post" >
    <div class="toolForm">
        <div class="toolFormTitle">Create a new form definition</div>
        %for label, input in inputs:
            <div class="form-row">
                <label>${label}</label>
                ${input.get_html()}
                <div style="clear: both"></div>
            </div>
        %endfor
        <div class="form-row">
            <input type="submit" name="create_form_button" value="Add fields"/>
        </div>
    </div>
</form>
