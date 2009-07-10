<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />


%if msg:
    ${render_msg( msg, messagetype )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">${form.name} - <i>${form.desc}</i></div>
    <form name="library" action="${h.url_for( controller='forms', action='manage' )}" method="post" >
        <table class = "grid">
            <tbody>
                %for index, field in enumerate(form.fields):
                    <tr>
                        <td>
                            <div class="form-row">
                                <label>${1+index}. Label</label>
                                <a>${field['label']}</a>
                                %if field['type'] == 'SelectField':
                                    <a id="${field['label']}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                                    %for option in field['selectlist']:
                                        <div popupmenu="${field['label']}-type-popup">
                                            <a class="action-button" href="" >${option}</a>
                                        </div>                                 
                                    %endfor
                                %endif                                    
                            </div>
                        </td>
                        <td>
                            <div class="form-row">
                                <label>Help text </label>
                                %if not field['helptext']:
                                    <a><i>No helptext</i></a>
                                %else:
                                    <a>${field['helptext']}</a>
                                %endif
                            </div>
                        </td>                            
                        <td>
                            <div class="form-row">
                                <label>Type:</label>
                                <a>${field['type']}</a>
                                %if field['type'] == 'SelectField':
                                    <a id="fieldtype-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                                    %for option in field['selectlist']:
                                        <div popupmenu="type-popup">
                                            <a class="action-button" href="" >${option}</a>
                                        </div>                                 
                                    %endfor
                                %endif
                            </div>
                        </td>
                        <td>
                            <div class="form-row">
                                <label>Required?</label>
                                <a>${field['required']}</a>
                            </div>
                        </td>
                    </tr>       
                %endfor
            </tbody>
        </table>            
        ##<input type="submit" name="save_changes_button" value="Back"/>
    </form>
    </div>
</div>