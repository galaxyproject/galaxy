<%inherit file="/embed_base.mako"/>
<%def name="render_item_links( workflow )">
	<a href="${h.url_for( controller='workflow', action='display_by_username_and_slug', username=workflow.user.username,
                          slug=item.slug, format='json-download' )}" title="Save Worflow" class="icon-button disk">
	${parent.render_item_links( workflow )}
</%def>
