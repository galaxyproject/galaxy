<%inherit file="/base.mako"/>
<%! from galaxy import model %>

##
## Page methods.
##

<%def name="title()">
	Sharing Workflow '${stored.name}'
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
	<style>
		div.indent
		{
			margin-left: 1em;
		}
		input.action-button
		{
			margin-left: 0;
		}
	</style>
</%def>

## Get display name for a class.
<%def name="get_class_display_name( a_class )">
<%
    if a_class is model.History:
        return "History"
    elif a_class is model.StoredWorkflow:
        return "Workflow"
    elif a_class is model.Page:
        return "Page"
%>
</%def>

##
## Page content.
##

<h2>Sharing Workflow '${stored.name}'</h2>

<div class="indent" style="margin-top: 2em">
<h3>Making Workflow Accessible via Link and Publishing It</h3>
    
    <div class="indent">
        %if stored.importable:
			<% 
				item_status = "accessible via link" 
				if stored.published:
					item_status = item_status + " and published"	
			%>
			This workflow <strong>${item_status}</strong>. 
			<div class="indent">
				<p>Anyone can view and import this workflow by visiting the following URL:
	            <% url = h.url_for( action='display_by_username_and_slug', username=trans.get_user().username, slug=stored.slug, qualified=True ) %>
				<blockquote>
	            	<a href="${url}">${url}</a>
				</blockquote>
			
				%if stored.published:
					This workflow is publicly listed and searchable in Galaxy's <a href='${h.url_for( action='list_published' )}'>Published Workflows</a> section.
				%endif
			</div>
			
			<p>You can:
			<div class="indent">
           	<form action="${h.url_for( action='sharing', id=trans.security.encode_id(stored.id) )}" 
					method="POST">
					%if not stored.published:
						## Item is importable but not published. User can disable importable or publish.
	               		<input class="action-button" type="submit" name="disable_link_access" value="Disable Access to Workflow Link">
						<div class="toolParamHelp">Disables workflow's link so that it is not accessible.</div>
						<br>
						<input class="action-button" type="submit" name="publish" value="Publish Workflow" method="POST">
						<div class="toolParamHelp">Publishes the workflow to Galaxy's <a href='${h.url_for( action='list_published' )}'>Published Workflows</a> section, where it is publicly listed and searchable.</div>

					<br>
					%else: ## stored.published == True
						## Item is importable and published. User can unpublish or disable import and unpublish.
						<input class="action-button" type="submit" name="unpublish" value="Unpublish Workflow">
						<div class="toolParamHelp">Removes workflow from Galaxy's <a href='${h.url_for( action='list_published' )}'>Published Workflows</a> section so that it is not publicly listed or searchable.</div>
						<br>
						<input class="action-button" type="submit" name="disable_link_access_and_unpubish" value="Disable Access to Workflow via Link and Unpublish">
						<div class="toolParamHelp">Disables workflow's link so that it is not accessible and removes workflow from Galaxy's <a href='${h.url_for( action='list_published' )}' target='_top'>Published Workflows</a> section so that it is not publicly listed or searchable.</div>
					%endif
					
           	</form>
			</div>
    
        %else:
    
            This workflow is currently restricted so that only you and the users listed below can access it. You can:
            <p>
            <form action="${h.url_for( action='sharing', id=trans.security.encode_id(stored.id) )}" method="POST">
				<input class="action-button" type="submit" name="make_accessible_via_link" value="Make Workflow Accessible via Link">
				<div class="toolParamHelp">Generates a web link that you can share with other people so that they can view and import the workflow.</div>
			
				<br>
            	<input class="action-button" type="submit" name="make_accessible_and_publish" value="Make Workflow Accessible and Publish" method="POST">
				<div class="toolParamHelp">Makes the workflow accessible via link (see above) and publishes the workflow to Galaxy's <a href='${h.url_for( action='list_published' )}' target='_top'>Published Workflows</a> section, where it is publicly listed and searchable.</div>
            </form>
        
        %endif
    </div>

<h3>Sharing Workflow with Specific Users</h3>

    <div class="indent">
        %if stored.users_shared_with:

            <p>
                The following users will see this workflow in their workflow list and will be
                able to run/view and import it.
            </p>
    
            <ul class="manage-table-actions">
                <li>
                    <a class="action-button" href="${h.url_for( action='share', id=trans.security.encode_id(stored.id) )}">
                        <span>Share with another user</span>
                    </a>
                </li>
            </ul>
        
            <table class="colored" border="0" cellspacing="0" cellpadding="0" width="100%">
                <tr class="header">
                    <th>Email</th>
                    <th></th>
                </tr>
                %for i, association in enumerate( stored.users_shared_with ):
                    <% user = association.user %>
                    <tr>
                        <td>
                            ${user.email}
                            <a id="user-${i}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                        </td>
                        <td>
                            <div popupmenu="user-${i}-popup">
                            <a class="action-button" href="${h.url_for( id=trans.security.encode_id( stored.id ), unshare_user=trans.security.encode_id( user.id ) )}">Unshare</a>
                            </div>
                        </td>
                    </tr>    
                %endfor
            </table>

        %else:

            <p>You have not shared this workflow with any users.</p>
    
            <a class="action-button" href="${h.url_for( action='share', id=trans.security.encode_id(stored.id) )}">
                <span>Share with another user</span>
            </a>
            <br>
    
        %endif
    </div>
</div>

<p><br><br>
<a href=${h.url_for( action="list" )}>Back to Workflows List</a>