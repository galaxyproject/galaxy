##
## A set of useful methods for displaying different items.
##

## Return a link to view a history.
<%def name="get_history_link( history, qualify=False )">
    %if history.slug and history.user.username:
        <% return h.url_for( controller='/history', action='display_by_username_and_slug', username=history.user.username, slug=history.slug, qualified=qualify ) %>
    %else:
        <% return h.url_for( controller='/history', action='view', id=trans.security.encode_id( history.id ), qualified=qualify ) %>
    %endif
</%def>