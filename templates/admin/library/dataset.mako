<%inherit file="/base.mako"/>
<%namespace file="/dataset/security_common.mako" import="render_permission_form" />
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/library/common.mako" import="render_available_templates" />


%if msg:
    ${render_msg( msg, messagetype )}
%endif

<%def name="title()">Edit Dataset Attributes</%def>

<%def name="datatype( dataset, datatypes )">
    <select name="datatype">
        ## $datatypes.sort()
        %for ext in datatypes:
            %if dataset.ext == ext:
                <option value="${ext}" selected="yes">${ext}</option>
            %else:
                <option value="${ext}">${ext}</option>
            %endif
        %endfor
    </select>
</%def>

<%
    roles = trans.app.model.Role.filter( trans.app.model.Role.table.c.deleted==False ).order_by( trans.app.model.Role.table.c.name ).all()
%>

%if isinstance( dataset, list ):
    <%
        name_str = '%d selected datasets' % len( dataset )
    %>
    ${render_permission_form( dataset[0], name_str, h.url_for( action='dataset' ), 'id', ",".join( [ str(d.id) for d in dataset ] ), roles )}
%else:
    ${render_permission_form( dataset, dataset.name, h.url_for( action='dataset' ), 'id', dataset.id, roles )}
%endif

%if dataset.library_dataset.library_folder_dataset_association == dataset:
    ${render_msg( 'You are currently viewing the latest version of this Library Dataset, you can go <a href="%s">here</a> to manage versions.' % ( h.url_for( controller='admin', action='library_dataset', id=dataset.library_dataset.id ) ), 'info' )}
%else:
    ${render_msg( 'You are currently viewing an expired version of this Library Dataset, you can go <a href="%s">here</a> to manage versions.' % ( h.url_for( controller='admin', action='library_dataset', id=dataset.library_dataset.id ) ), 'warning' )}
%endif

%if not isinstance( dataset, list ):
    <div class="toolForm">
        <div class="toolFormTitle">Edit Attributes</div>
        <div class="toolFormBody">
            <form name="edit_attributes" action="${h.url_for( controller='admin', action='dataset' )}" method="post">
                <input type="hidden" name="id" value="${dataset.id}"/>
                <div class="form-row">
                    <label>Name:</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="text" name="name" value="${dataset.name}" size="40"/>
                    </div>
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <label>Info:</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="text" name="info" value="${dataset.info}" size="40"/>
                    </div>
                    <div style="clear: both"></div>
                </div> 
                %for name, spec in dataset.metadata.spec.items():
                    %if spec.visible:
                        <div class="form-row">
                            <label>${spec.desc}:</label>
                            <div style="float: left; width: 250px; margin-right: 10px;">
                                ${dataset.metadata.get_html_by_name( name )}
                            </div>
                            <div style="clear: both"></div>
                        </div>
                    %endif
                %endfor
                <div class="form-row">
                    <input type="submit" name="save" value="Save"/>
                </div>
            </form>
            <form name="auto_detect" action="${h.url_for( controller='admin', action='dataset' )}" method="post">
                <input type="hidden" name="id" value="${dataset.id}"/>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="submit" name="detect" value="Auto-detect"/>
                </div>
                <div class="toolParamHelp" style="clear: both;">
                    This will inspect the dataset and attempt to correct the above column values
                    if they are not accurate.
                </div>
            </form>
        </div>
    </div>
    <p/>
    <div class="toolForm">
        <div class="toolFormTitle">Change data type</div>
        <div class="toolFormBody">
            <form name="change_datatype" action="${h.url_for( controller='admin', action='dataset' )}" method="post">
                <input type="hidden" name="id" value="${dataset.id}"/>
                <div class="form-row">
                    <label>New Type:</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        ${datatype( dataset, datatypes )}
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
%endif

${render_available_templates( dataset )}
