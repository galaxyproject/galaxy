<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<br/><br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='library_common', action='browse_library', cntrller=cntrller, id=library_id, use_panels=use_panels, show_deleted=show_deleted )}"><span>Browse this data library</span></a>
    </li>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Edit the template for the ${item_desc} '${item_name}'</div>
    <form id="edit_template" name="edit_template" action="${h.url_for( controller='library_common', action='edit_template', cntrller=cntrller, item_type=item_type, library_id=library_id, folder_id=folder_id, ldda_id=ldda_id, use_panels=use_panels, show_deleted=show_deleted )}" method="post" >
        <div class="toolFormBody">
            %for i, field in enumerate( widgets ):
                <div class="form-row">
                    <label>${field[ 'label' ]}</label>
                    ${field[ 'widget' ].get_html()}
                    <div class="toolParamHelp" style="clear: both;">
                        ${field[ 'helptext' ]}
                    </div>
                    <div style="clear: both"></div>
                </div>
            %endfor
            <div style="clear: both"></div>
            <div class="form-row">
                <input type="submit" name="edit_template_button" value="Save"/>
            </div>
        </div>
    </form>
</div>
