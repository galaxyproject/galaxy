<%inherit file="/base.mako"/>
<%namespace file="/dataset/security_common.mako" import="render_permission_form" />
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/library/common.mako" import="render_available_templates" />
<%namespace file="/library/common.mako" import="render_existing_library_item_info" />
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

<%
    roles = trans.app.model.Role.filter( trans.app.model.Role.table.c.deleted==False ).order_by( trans.app.model.Role.table.c.name ).all()
    data_list = util.listify( ldda )
    if len( data_list ) > 1:
        name_str = '%d selected datasets' % len( data_list )
    else:
        name_str = ldda.name
%>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

<div class="toolFormTitle">Manage the following selected datasets</div>

<p/>
<table cellspacing="0" cellpadding="5" border="0" width="100%" class="libraryTitle">
    %for ldd_assoc in data_list:
        <tr>
            <td>
                <div class="rowTitle">
                    <span class="historyItemTitle"><b>${ldd_assoc.name}</b></span>
                    <a id="ldd_assoc-${ldd_assoc.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                </div>
                <div popupmenu="ldd_assoc-${ldd_assoc.id}-popup">
                    <a class="action-button" href="${h.url_for( controller='library', action='library_dataset', id=ldd_assoc.library_dataset_id )}">Manage this dataset's versions</a>
                </div>
            </td>
            <td>
                %if ldd_assoc == ldd_assoc.library_dataset.library_dataset_dataset_association:
                    <i>This is the latest version of this library dataset</i>
                %else:
                    <font color="red"><i>This is an expired version of this library dataset</i></font>
                %endif
            </td>
        </tr>
    %endfor
</table>
<p/>

%if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS, dataset=ldda.dataset ):
    ${render_permission_form( data_list[0], name_str, h.url_for( action='library_dataset_dataset_association' ), 'id', ",".join( [ str( d.id ) for d in data_list ] ), roles )}
%endif

%if len( data_list ) == 1:
    %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY, library_item=ldda ):
        <div class="toolForm">
            <div class="toolFormTitle">Edit attributes of ${ldda.name}</div>
            <div class="toolFormBody">
                <form name="edit_attributes" action="${h.url_for( controller='library', action='library_dataset_dataset_association' )}" method="post">
                    <input type="hidden" name="id" value="${ldda.id}"/>
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
                <form name="auto_detect" action="${h.url_for( controller='library', action='library_dataset_dataset_association' )}" method="post">
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
            <div class="toolFormTitle">Change data type</div>
            <div class="toolFormBody">
                <form name="change_datatype" action="${h.url_for( controller='library', action='library_dataset_dataset_association' )}" method="post">
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
        <p/>
    %else:
        <div class="toolForm">
            <div class="toolFormTitle">View attributes of ${ldda.name}</div>
            <div class="toolFormBody">
                <div class="form-row">
                    <b>Name:</b> ${ldda.name}
                    <div style="clear: both"></div>
                    <b>Info:</b> ${ldda.info}
                    <div style="clear: both"></div>
                    <b>Data Format:</b> ${ldda.ext}
                    <div style="clear: both"></div>
                    %for name, spec in ldda.metadata.spec.items():
                        %if spec.visible:
                            <b>${spec.desc}:</b>
                            ${ldda.metadata.get( name )}
                            <div style="clear: both"></div>
                        %endif
                    %endfor
                </div>
            </div>
        </div>
        <div class="toolForm">
            ${render_existing_library_item_info( ldda.library_dataset )}
        </div>
    %endif
    %if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_ADD, library_item=ldda.library_dataset ):
        ${render_available_templates( ldda.library_dataset )}
    %endif
%endif
