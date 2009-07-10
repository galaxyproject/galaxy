<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />


%if msg:
    ${render_msg( msg, messagetype )}
%endif
<div class="toolForm">
    <div class="toolFormTitle">${title}</div>
    <div class="toolFormBody">
        <form name="event" action="${h.url_for( controller='requests_admin', action='save_state', new=True, sample_id_list=sample_id_list)}" method="post" >
                %for w in widgets:
                    <div class="form-row">
                        <label>
                            ${w[0]}
                        </label>
                        ${w[1].get_html()}
                        %if w[0] == 'Comments':
                            <div class="toolParamHelp" style="clear: both;">
                                Optional
                            </div>
                        %endif
                    </div>
                %endfor
            <div class="form-row">
                <input type="submit" name="add_event" value="Save"/>
            </div>
        </form>
    </div>
</div>