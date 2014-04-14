<%inherit file="/embed_base.mako"/>
<%!
    from galaxy.web.framework.helpers import iff
%>

<%def name="render_item_links( workflow )">
	<a href="${h.url_for( controller='workflow', action='display_by_username_and_slug', username=workflow.user.username,
                          slug=item.slug, format='json-download' )}" title="Save Worflow" class="icon-button disk">
	## FIXME: find and set appropriate icon for linking to workflow.
	<!--
	<a href="${h.url_for( controller='workflow', action='display_by_username_and_slug', username=workflow.user.username,
                          slug=item.slug, format='json' )}" title="Worflow Link for Import" class="icon-button TODO ">
	-->
	${parent.render_item_links( workflow )}
</%def>

<%def name="render_summary_content( workflow, steps )">

##    <ul>
##        <% num_steps = len ( steps ) %>
##        <li>${num_steps} step${iff( num_steps != 1, "s", "" )}
##        <li>Operations: ...
##    </ul>
</%def>
