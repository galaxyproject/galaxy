<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />


%if msg:
    ${render_msg( msg, messagetype )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Create a new form definition</div>
    <div class="toolFormBody">
        <form name="create_form" action="${h.url_for( controller='forms', action='new', create_form=True, new=False, create_fields=False  )}" method="post" >
            %for label, input in inputs:
                <div class="form-row">
                    <label>${label}</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        ${input.get_html()}
                    </div>
                    <div style="clear: both"></div>
                </div>
            %endfor
            <div class="form-row">
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="hidden" name="new" value="submitted" size="40"/>
                </div>
              <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <input type="submit" name="save_form" value="Add fields"/>
            </div>
        </form>
    </div>
</div>
