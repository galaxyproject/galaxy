<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />


<%def name="title()">Manage Form Definitions</%def>

## Render a row
<%def name="render_row( form, ctr )">
    %if ctr % 2 == 1:
        <tr class="odd_row">
    %else:
        <tr>
    %endif
        <td>
            <b><a href="${h.url_for( controller='forms', action='edit', form_id=form.id, read_only=True )}">${form.name}</a></b>
            <a id="form-${form.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
            <div popupmenu="form-${form.id}-popup">
                <a class="action-button" href="${h.url_for( action='edit', form_id=form.id, show_form=True )}">Edit form definition</a>
            </div>
        </td>
        <td><i>${form.desc}</i></td>
    </tr>
</%def>


<h2>
    %if deleted:
        Deleted 
    %endif
    Forms
</h2>



<ul class="manage-table-actions">
    %if not deleted:
        <li>
            <a class="action-button" href="${h.url_for( controller='forms', action='new', new=True )}">
            <img src="${h.url_for('/static/images/silk/add.png')}" />
            <span>Define a new form</span></a>
        </li>
    %endif
</ul>



%if msg:
    ${render_msg( msg, messagetype )}
%endif

%if not fdc_list:
    %if deleted:
        There are no deleted forms
    %else:
        There are no forms.
    %endif
%else:
    <table class="grid">
        <thead>
            <tr>
                <th>Name</th>
                <th>Description</th>
            </tr>
        </thead>
        <tbody>
            %for ctr, fdc in enumerate( fdc_list ):    
                <tr>
                ${render_row( fdc.latest_form, ctr )}
                </tr>          
            %endfor
        </tbody>
    </table>
%endif
