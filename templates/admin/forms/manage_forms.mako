<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="title()">Manage Form Definitions</%def>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

## Render a row
<%def name="render_row( form, ctr )">
    %if ctr % 2 == 1:
        <tr class="odd_row">
    %else:
        <tr>
    %endif
        <td>
            <a href="${h.url_for( controller='forms', action='edit', form_id=form.id, read_only=True )}">${form.name}</a>
            <a id="form-${form.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
            %if form.form_definition_current.deleted:
                <div popupmenu="form-${form.id}-popup">
                    <a class="action-button" href="${h.url_for( action='undelete', form_id=form.id )}">Undelete</a>
                </div>
            %else:
                <div popupmenu="form-${form.id}-popup">
                    <a class="action-button" href="${h.url_for( action='edit', form_id=form.id, show_form=True )}">Edit form definition</a>
                    <a class="action-button" confirm="Click OK to delete the form ${form.name}." href="${h.url_for( action='delete', form_id=form.id )}">Delete</a>
                </div>
            %endif
        </td>
        <td><i>${form.desc}</i></td>
        <td>${form.type}</td>
    </tr>
</%def>

<h2>Forms</h2>

<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='forms', action='new' )}">
        <span>Create a new form</span></a>
    </li>
</ul>

%if not all_forms:
    There are no forms.
%else:
    <div class="grid-header">
        %for i, filter in enumerate( ['Active', 'Deleted', 'All'] ):
            %if i > 0:    
                <span>|</span>
            %endif
            %if show_filter == filter:
                <span class="filter"><a href="${h.url_for( controller='forms', action='manage', show_filter=filter )}"><b>${filter}</b></a></span>
            %else:
                <span class="filter"><a href="${h.url_for( controller='forms', action='manage', show_filter=filter )}">${filter}</a></span>
            %endif
        %endfor
    </div>
    <table class="grid">
        <thead>
            <tr>
                <th>Name</th>
                <th>Description</th>
                <th>Type</th>
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
