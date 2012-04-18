<%inherit file="/webapps/galaxy/base_panels.mako"/>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.active_view="shared"
    self.message_box_visible=False
%>
</%def>

<%def name="center_panel()">

    <div style="overflow: auto; height: 100%;">
        <div class="page-container" style="padding: 10px;">
            ${h.to_unicode( grid )}

			<br><br>
			<h2>Pages shared with you by others</h2>

			%if shared_by_others:
			    <table class="colored" border="0" cellspacing="0" cellpadding="0" width="100%">
			        <tr class="header">
			            <th>Title</th>
			            <th>Owner</th>
			            <th></th>
			        </tr>
			        %for i, association in enumerate( shared_by_others ):
			            <% page = association.page %>
			            <tr>
			                <td>
			                    <a class="menubutton" id="shared-${i}-popup" href="${h.url_for( action='display_by_username_and_slug', username=page.user.username, slug=page.slug)}">${page.title}</a>
			                </td>
			                <td>${page.user.username}</td>
			                <td>
			                    <div popupmenu="shared-${i}-popup">
									<a class="action-button" href="${h.url_for( action='display_by_username_and_slug', username=page.user.username, slug=page.slug)}" target="_top">View</a>
			                    </div>
			                </td>
			            </tr>    
			        %endfor
			    </table>
			%else:

			    No pages have been shared with you.

			%endif

        </div>
    </div>

</%def>
