<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if msg:
    ${render_msg( msg, messagetype )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Create a new form definition</div>
    <div class="toolFormBody">
        <form name="create_form" action="${h.url_for( controller='forms', action='new', create_form=True )}" enctype="multipart/form-data" method="post" >
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
        </form>
    </div>
</div>
