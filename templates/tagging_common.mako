<%! 
    from cgi import escape 
    from galaxy.web.framework.helpers import iff
    from random import random
    from sys import maxint
    from math import floor
    from galaxy.model import Tag, ItemTagAssociation
%>

## Render a tagging element if there is a tagged_item.
%if tagged_item is not None:
    %if tag_type == "individual":
        ${render_individual_tagging_element( user=user, tagged_item=tagged_item, elt_context=elt_context, in_form=in_form, input_size=input_size, tag_click_fn=tag_click_fn, use_toggle_link=use_toggle_link )}
    %elif tag_type == "community":
        ${render_community_tagging_element(tagged_item=tagged_item, elt_context=elt_context, tag_click_fn=tag_click_fn)}
    %endif
%endif

## Render HTML for a list of tags.
<%def name="render_tagging_element_html(elt_id=None, tags=None, editable=True, use_toggle_link=True, input_size='15', in_form=False, tag_type='individual', render_add_tag_button=True)">
    ## Useful attributes.
    <% 
        num_tags = len( tags )
    %>
    <div class="tag-element"
        %if elt_id:
            id="${elt_id}"
        %endif
        ## Do not display element if there are no tags and it is not editable.
        %if num_tags == 0 and not editable:
            style="display: none"
        %endif
    >
        %if use_toggle_link:
            <a class="toggle-link" href="#">${num_tags} Tag${iff( num_tags == 1, "", "s")}</a>
        %endif
        <div class="tag-area 
            %if tag_type == 'individual':
                individual-tag-area
            %endif
        ">

            ## Build buttons for current tags.
            %for tag in tags:
                <%
                    ## Handle both Tag and ItemTagAssociation objects.
                    if isinstance( tag, Tag ):
                        tag_name = tag.name
                        tag_value = None
                    elif isinstance( tag, ItemTagAssociation ):
                        tag_name = tag.user_tname
                        tag_value = tag.user_value
                    ## Convert tag name, value to unicode.
                    if isinstance( tag_name, str ):
                        tag_name = unicode( escape( tag_name ), 'utf-8' )
                        if tag_value:
                            tag_value = unicode( escape( tag_value ), 'utf-8' )
                    if tag_value:
                        tag_str = tag_name + ":" + tag_value
                    else:
                        tag_str = tag_name
                %>
                <span class="tag-button">
                    <span class="tag-name">${tag_str}</span>
                    %if editable:
                        <img class="delete-tag-img" src="${h.url_for('/static/images/delete_tag_icon_gray.png')}"/>
                    %endif
                </span>
            %endfor
            
            ## Add tag input field. If element is in form, tag input is a textarea; otherwise element is a input type=text.
            %if editable:
                %if in_form:
                    <textarea class="tag-input" rows='1' cols='${input_size}'></textarea>
                %else:
                    <input class="tag-input" type='text' size='${input_size}'/>
                %endif
                ## Add "add tag" button.
                %if render_add_tag_button:
                    <img src='${h.url_for('/static/images/fugue/tag--plus.png')}' class="add-tag-button" title="Add tags"/>
                %endif
            %endif
        </div>
    </div>
</%def>

## Render tool tagging elements
<%def name="render_tool_tagging_elements()">
    <%
        elt_id = int ( floor ( random()*maxint ) )
        tags = trans.app.tag_handler.get_tool_tags( trans )
    %>
    ${self.render_tagging_element_html(elt_id=elt_id, \
                                        tags=tags, \
                                        editable=False, \
                                        use_toggle_link=False )}
    <script type="text/javascript">
        init_tag_click_function($('#${elt_id}'), tool_tag_click);
    </script>
</%def>

## Render community tagging element.
<%def name="render_community_tagging_element(tagged_item=None, elt_context=None, use_toggle_link=False, tag_click_fn='default_tag_click_fn')">
    ## Build HTML.
    <% 
        elt_id = int ( floor ( random()*maxint ) ) 
        community_tags = trans.app.tag_handler.get_community_tags( trans, item=tagged_item, limit=5 )
    %>
    ${self.render_tagging_element_html(elt_id=elt_id, \
                                        tags=community_tags, \
                                        use_toggle_link=use_toggle_link, \
                                        editable=False, tag_type="community")}
    
    ## Set up tag click function.
    <script type="text/javascript">
        init_tag_click_function($('#${elt_id}'), ${tag_click_fn});
    </script>
</%def>


## Render individual tagging element.
<%def name="render_individual_tagging_element(user=None, tagged_item=None, elt_context=None, use_toggle_link=True, in_form=False, input_size='15', tag_click_fn='default_tag_click_fn', get_toggle_link_text_fn='default_get_toggle_link_text_fn', editable=True, render_add_tag_button=True)">
    ## Useful attributes.
    <%
        # Useful ids.
        tagged_item_id = str( trans.security.encode_id ( tagged_item.id ) )
        elt_id = int ( floor ( random()*maxint ) )
        
        # Get list of user's item tags. TODO: implement owner_tags for all taggable objects and use here.
        item_tags = [ tag for tag in tagged_item.tags if ( tag.user == user ) ]
    %>
    
    ## Build HTML.
    ${self.render_tagging_element_html(elt_id=elt_id, tags=item_tags, editable=editable, use_toggle_link=use_toggle_link, input_size=input_size, in_form=in_form, render_add_tag_button=render_add_tag_button)}
    
    ## Build script that augments tags using progressive javascript.
    <script type="text/javascript">
        //
        // Set up autocomplete tagger.
        //

        //
        // Default function get text to display on the toggle link.
        //
        var default_get_toggle_link_text_fn = function(tags)
        {
            var text = "";
            var num_tags = obj_length(tags);
            if (num_tags != 0)
              {
                text = num_tags + (num_tags != 1 ? " Tags" : " Tag");
                /*
                // Show first N tags; hide the rest.
                var max_to_show = 1;
    
                // Build tag string.
                var tag_strs = new Array();
                var count = 0;
                for (tag_name in tags)
                  {
                    tag_value = tags[tag_name];
                    tag_strs[tag_strs.length] = build_tag_str(tag_name, tag_value);
                    if (++count == max_to_show)
                      break;
                  }
                tag_str = tag_strs.join(", ");
            
                // Finalize text.
                var num_tags_hiding = num_tags - max_to_show;
                text = "Tags: " + tag_str + 
                  (num_tags_hiding != 0 ? " and " + num_tags_hiding + " more" : "");
                */
              }
            else
              {
                // No tags.
                text = "Add tags";
              }
            return text;
        };
        
        // Default function to handle a tag click.
        var default_tag_click_fn = function(tag_name, tag_value) { };
        
        <%
            ## Build dict of tag name, values.
            tag_names_and_values = dict()
            for tag in item_tags:
                tag_name = tag.user_tname
                tag_value = ""
                if tag.value is not None:
                    tag_value = tag.user_value
                ## Tag names and values may be string or unicode object.
                if isinstance( tag_name, str ):
                    tag_names_and_values[unicode(tag_name, 'utf-8')] = unicode(tag_value, 'utf-8')
                else: ## isInstance( tag_name, unicode ):
                    tag_names_and_values[tag_name] = tag_value
        %>
        var options =
        {
            tags : ${h.dumps(tag_names_and_values)},
            editable : ${iff( editable, 'true', 'false' )},
            get_toggle_link_text_fn: ${get_toggle_link_text_fn},
            tag_click_fn: ${tag_click_fn},
            ## Use forward slash in controller to suppress route memory.
            ajax_autocomplete_tag_url: "${h.url_for( controller='/tag', action='tag_autocomplete_data', item_id=tagged_item_id, item_class=tagged_item.__class__.__name__ )}",
            ajax_add_tag_url: "${h.url_for( controller='/tag', action='add_tag_async', item_id=tagged_item_id, item_class=tagged_item.__class__.__name__, context=elt_context )}",
            ajax_delete_tag_url: "${h.url_for( controller='/tag', action='remove_tag_async', item_id=tagged_item_id, item_class=tagged_item.__class__.__name__, context=elt_context )}",
            delete_tag_img: "${h.url_for('/static/images/delete_tag_icon_gray.png')}",
            delete_tag_img_rollover: "${h.url_for('/static/images/delete_tag_icon_white.png')}",
            use_toggle_link: ${iff( use_toggle_link, 'true', 'false' )}
         };
         
        $('#${elt_id}').autocomplete_tagging(options);
    </script>
    
    ## Use style to hide/display the tag area.
    <style>
    .tag-area {
        display: ${iff( use_toggle_link, "none", "block" )};
    }
    </style>

    <noscript>
    <style>
    .tag-area {
        display: block;
    }
    </style>
    </noscript>
</%def>
