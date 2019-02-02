<%namespace file="/message.mako" import="render_msg" />

<%!
   def inherit(context):
       if context.get('use_panels'):
           return '/webapps/tool_shed/base_panels.mako'
       else:
           return '/base.mako'
%>

<%inherit file="${inherit(context)}"/>

<%def name="stylesheets()">
    ${parent.stylesheets()}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
</%def>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormBody">
        <div class="form-row">
            <div class="warningmessage">
                Importing may take a while, depending upon the contents of the capsule.
                Wait until this page refreshes after clicking the <b>Import</b> button below.
            </div>
            <div style="clear: both"></div>
        </div>
    </div>
</div>
        
<div class="toolForm">
    <div class="toolFormTitle">Repository capsule information</div>
    <div class="toolFormBody">
        <div class="form-row">
            <label>Date and time exported:</label>
            ${export_info_dict.get( 'export_time', 'unknown' ) | h}
        </div>
        <div style="clear: both"></div>
        <div class="form-row">
            <label>Exported from Tool Shed:</label>
            ${export_info_dict.get( 'tool_shed', 'unknown' ) | h}
        </div>
        <div style="clear: both"></div>
        <div class="form-row">
            <label>Repository name:</label>
            ${export_info_dict.get( 'repository_name', 'unknown' ) | h}
        </div>
        <div style="clear: both"></div>
        <div class="form-row">
            <label>Repository owner:</label>
            ${export_info_dict.get( 'repository_owner', 'unknown' ) | h}
        </div>
        <div style="clear: both"></div>
        <div class="form-row">
            <label>Changeset revision:</label>
            ${export_info_dict.get( 'changeset_revision', 'unknown' ) | h}
        </div>
        <div style="clear: both"></div>
        <div class="form-row">
            <label>Repository dependencies included in capsule?:</label>
            ${export_info_dict.get( 'export_repository_dependencies', 'unknown' ) | h}
        </div>
        <div style="clear: both"></div>
    </div>
</div>
<div class="toolForm">
    <div class="toolFormBody">
        <div class="form-row">
            <div class="warningmessage">
                <p>
                    Exported archives for each of the following repositories are included in the capsule.
                </p>
                <p>
                    The <b>Status</b> column will display an entry starting with the word <b>Exists</b> for those repositories
                    that already exist in this Tool Shed.  These repositories will not be created, but the existing repository
                    will be used.  Existing repositories that are deprecated or deleted must be manually altered appropriately.
                </p>
                <p>
                    If you are not an admin user in this Tool Shed and you are not a member of the <b>Intergalactic Utilities
                    Commission</b> defined for this Tool Shed, you will only be able to import repository archives whose
                    associated owner is you.  The <b>Status</b> column for repository archive that you are not authorized to
                    import will display the entry <b>Not authorized to import</b>.  Contact someone that is authorized to import
                    these repository archives in this Tool Shed if necessary.
                </p>
                <p>
                    Repositories that do not yet exist in this Tool Shed (and whose archives you are authorized to import) will
                    be created in the order defined by the following list.
                </p>
            </div>
            <div style="clear: both"></div>
        </div>
    </div>
</div>
<div class="toolForm">
    <div class="toolFormTitle">Import capsule</div>
        <form id="import_form" name="import_form" action="${h.url_for( controller='repository', action='import_capsule' )}" enctype="multipart/form-data" method="post">
            <div class="form-row">
                <input type="hidden" name="encoded_file_path" value="${encoded_file_path}" />
            </div>
            <div class="form-row">
                <table class="grid">
                    <tr>
                        <th bgcolor="#D8D8D8">Name</th>
                        <th bgcolor="#D8D8D8">Owner</th>
                        <th bgcolor="#D8D8D8">Changeset Revision</th>
                        <th bgcolor="#D8D8D8">Type</th>
                        <th bgcolor="#D8D8D8">Status</th>
                    </tr>
                    %for repository_status_info_dict in repository_status_info_dicts:
                        <tr>
                            <td>${ repository_status_info_dict[ 'name' ] | h }</td>
                            <td>${ repository_status_info_dict[ 'owner' ] | h }</td>
                            <td>${ repository_status_info_dict[ 'changeset_revision' ] | h }</td>
                            <td>
                                <%
                                    # Get the label for the repository type.
                                    type = repository_status_info_dict[ 'type' ]
                                    type_class = trans.app.repository_types_registry.get_class_by_label( type )
                                    type_label = type_class.label
                                %>
                                ${ type_label | h }
                            </td>
                            <td>
                                %if repository_status_info_dict[ 'status' ] is None:
                                    &nbsp;
                                %else:
                                    ${ repository_status_info_dict[ 'status' ] | h }
                                %endif
                            </td>
                        </tr>
                    %endfor
                </table>
            </div>
            <div style="clear: both"></div>
            <div class="form-row">
                <input type="submit" class="primary-button" name="import_capsule_button" value="Import">
            </div>
        </form>
    </div>
</div>
