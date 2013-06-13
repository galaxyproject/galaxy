<%inherit file="/webapps/galaxy/base_panels.mako"/>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.active_view="workflow"
    self.message_box_visible=False
%>
</%def>

<%def name="title()">Workflow home</%def>

<%def name="center_panel()">
    <div style="overflow: auto; height: 100%;">
        <div class="page-container" style="padding: 10px;">
            %if message:
                <%
                    try:
                        status
                    except:
                        status = "done"
                %>
                <p />
                <div class="${status}message">
                    ${h.to_unicode( message )}
                </div>
            %endif

            <h2>Your workflows</h2>

            <ul class="manage-table-actions">
                <li>
                    <a class="action-button" href="${h.url_for( controller='workflow', action='create' )}">
                        <img src="${h.url_for('/static/images/silk/add.png')}" />
                        <span>Create new workflow</span>
                    </a>
                </li>
                <li>
                    <a class="action-button" href="${h.url_for( controller='workflow', action='import_workflow' )}">
                        <img src="${h.url_for('/static/images/fugue/arrow-090.png')}" />
                        <span>Upload or import workflow</span>
                    </a>
                </li>
            </ul>

            %if workflows:
                <table class="manage-table colored" border="0" cellspacing="0" cellpadding="0" style="width:100%;">
                    <tr class="header">
                        <th>Name</th>
                        <th># of Steps</th>
                        ## <th>Last Updated</th>
                        <th></th>
                    </tr>
                    %for i, workflow in enumerate( workflows ):
                        <tr>
                            <td>
                                <div class="menubutton" style="float: left;" id="wf-${i}-popup">
                                ${h.to_unicode( workflow.name ) | h}
                                </div>
                            </td>
                            <td>${len(workflow.latest_workflow.steps)}</td>
                            ## <td>${str(workflow.update_time)[:19]}</td>
                            <td>
                                <div popupmenu="wf-${i}-popup">
                                <a class="action-button" href="${h.url_for( controller='workflow', action='editor', id=trans.security.encode_id( workflow.id ) )}" target="_parent">Edit</a>
                                <a class="action-button" href="${h.url_for( controller='root', action='index', workflow_id=trans.security.encode_id( workflow.id ) )}" target="_parent">Run</a>
                                <a class="action-button" href="${h.url_for( controller='workflow', action='sharing', id=trans.security.encode_id( workflow.id ) )}">Share or Publish</a>
                                <a class="action-button" href="${h.url_for( controller='workflow', action='export', id=trans.security.encode_id( workflow.id ) )}">Download or Export</a>
                                <a class="action-button" href="${h.url_for( controller='workflow', action='copy', id=trans.security.encode_id( workflow.id ) )}">Copy</a>
                                <a class="action-button" href="${h.url_for( controller='workflow', action='rename', id=trans.security.encode_id( workflow.id ) )}">Rename</a>
                                <a class="action-button" href="${h.url_for( controller='workflow', action='display_by_id', id=trans.security.encode_id( workflow.id ) )}" target="_top">View</a>
                                <a class="action-button" confirm="Are you sure you want to delete workflow '${h.to_unicode( workflow.name ) | h}'?" href="${h.url_for( controller='workflow', action='delete', id=trans.security.encode_id( workflow.id ) )}">Delete</a>
                                </div>
                            </td>
                        </tr>
                    %endfor
                </table>
            %else:
                You have no workflows.
            %endif

            <h2>Workflows shared with you by others</h2>

            %if shared_by_others:
                <table class="colored" border="0" cellspacing="0" cellpadding="0" width="100%">
                    <tr class="header">
                        <th>Name</th>
                        <th>Owner</th>
                        <th># of Steps</th>
                        <th></th>
                    </tr>
                    %for i, association in enumerate( shared_by_others ):
                        <% workflow = association.stored_workflow %>
                        <tr>
                            <td>
                                <a class="menubutton" id="shared-${i}-popup" href="${h.url_for( controller='workflow', action='run', id=trans.security.encode_id(workflow.id) )}">${h.to_unicode( workflow.name )}</a>
                            </td>
                            <td>${workflow.user.email}</td>
                            <td>${len(workflow.latest_workflow.steps)}</td>
                            <td>
                                <div popupmenu="shared-${i}-popup">
                                    <a class="action-button" href="${h.url_for( controller='workflow', action='display_by_username_and_slug', username=workflow.user.username, slug=workflow.slug )}" target="_top">View</a>
                                    <a class="action-button" href="${h.url_for( controller='workflow', action='run', id=trans.security.encode_id( workflow.id ) )}">Run</a>
                                    <a class="action-button" href="${h.url_for( controller='workflow', action='copy', id=trans.security.encode_id( workflow.id ) )}">Copy</a>
                                    <a class="action-button" confirm="Are you sure you want to remove the shared workflow '${h.to_unicode( workflow.name ) | h}'?" href="${h.url_for( controller='workflow', action='sharing', unshare_me=True, id=trans.security.encode_id( workflow.id ))}">Remove</a>
                                </div>
                            </td>
                        </tr>
                    %endfor
                </table>
            %else:
                No workflows have been shared with you.
            %endif

            <h2>Other options</h2>

            <a class="action-button" href="${h.url_for( controller='workflow', action='configure_menu' )}">
                <span>Configure your workflow menu</span>
            </a>
        </div>
    </div>
</%def>
