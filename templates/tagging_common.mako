<%namespace file="/display_common.mako" import="get_controller_name, modern_route_for_controller" />
<%!
from markupsafe import escape
%>

## Render a tagging element if there is a tagged_item.
%if tagged_item is not None:
    %if tag_type == "individual":
        ${render_individual_tagging_element(
            user=user, 
            tagged_item=tagged_item, 
            elt_context=elt_context,
            tag_click_fn=tag_click_fn, 
            use_toggle_link=use_toggle_link
        )}
    %elif tag_type == "community":
        ${render_community_tagging_element(
            tagged_item=tagged_item, 
            elt_context=elt_context, 
            tag_click_fn=tag_click_fn
        )}
    %endif
%endif


<%def name="render_community_tagging_element(
    tagged_item=None, 
    elt_context=None, 
    use_toggle_link=False,
    tag_click_fn='default_tag_click_fn')">
    
    <%
        tagged_item_id = str( trans.security.encode_id ( tagged_item.id ) )
        controller_name = get_controller_name(tagged_item)
        click_url = h.url_for( controller='/' + modern_route_for_controller(controller_name) , action='list_published')
        community_tags = trans.app.tag_handler.get_community_tags( item=tagged_item, limit=5 )

        ## Having trouble converting list of tags into a plain array, this just
        ## just plucks out the name
        community_tag_names = []
        for tag in community_tags:
            community_tag_names.append(escape(tag.name))
    %>
    
    <div id="tags-community-${controller_name}-${tagged_item_id}"></div>

    <script type="text/javascript">
        config.addInitialization(function(galaxy, config) {
            var container = document.getElementById("tags-community-${controller_name}-${tagged_item_id}");
            var options = {
                tags: ${h.dumps(community_tag_names)},
                id: "${tagged_item_id}",
                itemClass: "${tagged_item.__class__.__name__}",
                context: "${elt_context}",
                tagClickFn: "${tag_click_fn}",
                clickUrl: "${click_url}",
                disabled: true
            }
            bundleEntries.mountMakoTags(options, container);
        });
    </script>
</%def>


<%def name="render_individual_tagging_element(
    user=None, 
    tagged_item=None,
    elt_context=None,
    use_toggle_link=True,
    tag_click_fn='default_tag_click_fn',
    get_toggle_link_text_fn='default_get_toggle_link_text_fn',
    editable=True)">

    <%
        tagged_item_id = str( trans.security.encode_id ( tagged_item.id ) )
        item_tags = [ tag for tag in tagged_item.tags if ( tag.user == user ) ]

        item_tag_names = []
        for ta in item_tags:
            item_tag_names.append(escape(f"#{ta.value}" if ta.value else ta.tag.name))
    %>

    <div id="tags-${tagged_item_id}"></div>

    <script type="text/javascript">
        config.addInitialization(function(galaxy, config) {
            var container = document.getElementById("tags-${tagged_item_id}");

            var options = {
                id: "${tagged_item_id}",
                context: "${elt_context}",
                tagClickFn: "${tag_click_fn}",
                disabled: !${h.to_js_bool(editable)},
                itemClass: "${tagged_item.__class__.__name__}",
                tags: ${h.dumps(item_tag_names)}
            }

            bundleEntries.mountMakoTags(options, container);
        });
    </script>

</%def>


<%def name="community_tag_js( controller_name )">
## TODO: Note that this function no longer has anything to do with community
## tags. the ratings code and tagging initialization were previously co-mingled
## in here. Will remove this script when we write the ratings components

## set up comminity tag and rating handling - used for page start up / set up
## controller_name: the model controller for the item being tagged - generally gotten with get_controller_name( item )
<script type="text/javascript">

    // Map item rating to number of stars to show.
    function map_rating_to_num_stars(rating) {
        if (rating <= 0)
            return 0;
        else if (rating > 0 && rating <= 1.5)
            return 1;
        else if (rating > 1.5 && rating <= 2.5)
            return 2;
        else if (rating > 2.5 && rating <= 3.5)
            return 3;
        else if (rating > 3.5 && rating <= 4.5)
            return 4;
        else if (rating > 4.5)
            return 5;
    }

    // Init. on document load.
    $(function() {
        // Set links to Galaxy screencasts to open in overlay.
        $(this).find("a[href^='http://screencast.g2.bx.psu.edu/']").each( function() {
            $(this).click( function() {
                var href = $(this).attr('href');
                show_in_overlay(
                    {
                        url: href,
                        width: 640,
                        height: 480,
                        scroll: 'no'
                    }
                );
                return false;
            });
        });

        // Init user item rating.
        $('.user_rating_star').rating({
            callback: function(rating, link) {
                $.ajax({
                    type: "GET",
                    url: "${h.url_for ( controller='/' + controller_name , action='rate_async' )}",
                    data: { id : "${trans.security.encode_id( item.id )}", rating : rating },
                    dataType: 'json',
                    error: function() { alert( "Rating submission failed" ); },
                    success: function( community_data ) {
                        $('#rating_feedback').show();
                        $('#num_ratings').text(Math.round(community_data[1]*10)/10);
                        $('#ave_rating').text(community_data[0]);
                        $('.community_rating_star').rating('readOnly', false);
                        $('.community_rating_star').rating('select', map_rating_to_num_stars(community_data[0])-1);
                        $('.community_rating_star').rating('readOnly', true);
                    }
                });
            },
            required: true // Hide cancel button.
        });
    });
</script>
</%def>
