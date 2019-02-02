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
                Click the <b>Create Docker Image</b> button below to create a Docker Image that will install the following repositories.
            </div>
            <div style="clear: both"></div>
        </div>
    </div>
</div>
<div class="toolForm">
    <div class="toolFormTitle">Repositories for inclusion in Docker Image</div>
        <form id="docker_image_form" name="docker_image_form" action="${h.url_for( controller='repository', action='create_galaxy_docker_image' )}" enctype="multipart/form-data" method="post">
            <div class="form-row">
                <input type="hidden" name="id" value="${id}" />
            </div>
            <div class="form-row">
                <table class="grid">
                    <tr>
                        <th bgcolor="#D8D8D8">Name</th>
                        <th bgcolor="#D8D8D8">Owner</th>
                        <th bgcolor="#D8D8D8">Type</th>
                    </tr>
                    %for repository_tup in repository_tups:
                        <% name, owner, type = repository_tup %>
                        <tr>
                            <td>${ name | h }</td>
                            <td>${ owner | h }</td>
                            <td>${ type | h }</td>
                        </tr>
                    %endfor
                </table>
            </div>
            <div style="clear: both"></div>
            <div class="form-row">
                <input type="submit" class="primary-button" name="create_docker_image_button" value="Create Docker Image">
            </div>
        </form>
    </div>
</div>
