<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/library/common.mako" import="render_available_templates" />
<%namespace file="/admin/library/common.mako" import="render_existing_library_item_info" />
<% from galaxy import util %>

<%def name="title()">Edit Dataset Attributes</%def>

<%def name="datatype( ldda, datatypes )">
    <select name="datatype">
        %for ext in datatypes:
            %if ldda.ext == ext:
                <option value="${ext}" selected="yes">${ext}</option>
            %else:
                <option value="${ext}">${ext}</option>
            %endif
        %endfor
    </select>
</%def>

%if ldda == ldda.library_dataset.library_dataset_dataset_association:
    <b><i>This is the latest version of this library dataset</i></b>
%else:
    <font color="red"><b><i>This is an expired version of this library dataset</i></b></font>
%endif
<p/>
            
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='admin', action='browse_library', id=library_id )}"><span>Browse this library</span></a>
    </li>
</ul>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Edit attributes of ${ldda.name}</div>
    <div class="toolFormBody">
        <form name="edit_attributes" action="${h.url_for( controller='admin', action='library_dataset_dataset_association', library_id=library_id, folder_id=ldda.library_dataset.folder.id, information=True )}" method="post">
            <input type="hidden" name="id" value="${ldda.id}"/>
            <br/>
            <div class="form-row">
                <label>Name:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="name" value="${ldda.name}" size="40"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Info:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="info" value="${ldda.info}" size="40"/>
                </div>
                <div style="clear: both"></div>
            </div> 
            %for name, spec in ldda.metadata.spec.items():
                %if spec.visible:
                    <div class="form-row">
                        <label>${spec.desc}:</label>
                        <div style="float: left; width: 250px; margin-right: 10px;">
                            ${ldda.metadata.get_html_by_name( name )}
                        </div>
                        <div style="clear: both"></div>
                    </div>
                %endif
            %endfor
            <div class="form-row">
                <input type="submit" name="save" value="Save"/>
            </div>
        </form>
        <form name="auto_detect" action="${h.url_for( controller='admin', action='library_dataset_dataset_association', library_id=library_id, folder_id=ldda.library_dataset.folder.id, information=True )}" method="post">
            <input type="hidden" name="id" value="${ldda.id}"/>
            <div style="float: left; width: 250px; margin-right: 10px;">
                <input type="submit" name="detect" value="Auto-detect"/>
            </div>
            <div class="toolParamHelp" style="clear: both;">
                This will inspect the dataset and attempt to correct the above column values if they are not accurate.
            </div>
        </form>
    </div>
</div>
<p/>
<div class="toolForm">
    <div class="toolFormTitle">Change data type of ${ldda.name}</div>
    <div class="toolFormBody">
        <form name="change_datatype" action="${h.url_for( controller='admin', action='library_dataset_dataset_association', library_id=library_id, folder_id=ldda.library_dataset.folder.id, information=True )}" method="post">
            <input type="hidden" name="id" value="${ldda.id}"/>
            <div class="form-row">
                <label>New Type:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    ${datatype( ldda, datatypes )}
                </div>
                <div class="toolParamHelp" style="clear: both;">
                    This will change the datatype of the existing dataset
                    but <i>not</i> modify its contents. Use this if Galaxy
                    has incorrectly guessed the type of your dataset.
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <input type="submit" name="change" value="Save"/>
            </div>
        </form>
    </div>
</div>

${render_existing_library_item_info( ldda )}

${render_available_templates( ldda, library_id )}
