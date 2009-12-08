<%! 
    from cgi import escape 
    from galaxy.web.framework.helpers import iff
%>
## Render a tagging element if there is a tagged_item.
%if tagged_item is not None:
    ${render_tagging_element(tagged_item=tagged_item, elt_context=elt_context, in_form=in_form, input_size=input_size, tag_click_fn=tag_click_fn)}
%endif

## Render HTML for a tagging element.
<%def name="render_tagging_element_html(tagged_item=None, editable=True, use_toggle_link=True, input_size='15', in_form=False)">
    ## Useful attributes.
    <% 
        tagged_item_id = str( trans.security.encode_id (tagged_item.id) )
        elt_id = "tag-element-" + tagged_item_id
    %>
    <div id="${elt_id}" class="tag-element">
        %if use_toggle_link:
            <a id="toggle-link-${tagged_item_id}" class="toggle-link" href="#">${len(tagged_item.tags)} Tags</a>
        %endif
        <div id="tag-area-${tagged_item_id}" class="tag-area">

            ## Build buttons for current tags.
            %for tag in tagged_item.tags:
                <%
                    tag_name = tag.user_tname
                    tag_value = None
                    if tag.value is not None:
                        tag_value = tag.user_value
                    ## Convert tag name, value to unicode.
                    if isinstance( tag_name, str ):
                        tag_name = unicode( escape( tag_name ), 'utf-8' )
                        if tag_value:
                            tag_value = unicode( escape( tag_value ), 'utf-8' )
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
                    <textarea id='tag-input' class="tag-input" rows='1' cols='${input_size}'></textarea>
                %else:
                    <input id='tag-input' class="tag-input" type='text' size='${input_size}'></input>
                %endif
                ## Add "add tag" button.
                <img src='${h.url_for('/static/images/add_icon.png')}' rollover='${h.url_for('/static/images/add_icon_dark.png')}' class="add-tag-button"/>
            %endif
        </div>
    </div>
</%def>


## Render the tags 'tags' as an autocomplete element.
<%def name="render_tagging_element(tagged_item=None, elt_context=None, use_toggle_link=True, in_form=False, input_size='15', tag_click_fn='default_tag_click_fn', get_toggle_link_text_fn='default_get_toggle_link_text_fn', editable=True)">
    ## Useful attributes.
    <% 
        tagged_item_id = str( trans.security.encode_id (tagged_item.id) )
        elt_id = "tag-element-" + tagged_item_id
    %>
    
    ## Build HTML.
    ${self.render_tagging_element_html(tagged_item, editable, use_toggle_link, input_size, in_form)}
    
    ## Build script that augments tags using progressive javascript.
    <script type="text/javascript">
        //
        // Set up autocomplete tagger.
        //
        <%
            ## Build string of tag name, values.
            tag_names_and_values = dict()
            for tag in tagged_item.tags:
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
    
        //
        // Default function get text to display on the toggle link.
        //
        var default_get_toggle_link_text_fn = function(tags)
        {
            var text = "";
            var num_tags = array_length(tags);
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
        var default_tag_click_fn = function(tag_name, tag_value) {};
        
        var options =
        {
            tags : ${h.to_json_string(tag_names_and_values)},
            editable : ${iff( editable, 'true', 'false' )},
            get_toggle_link_text_fn: ${get_toggle_link_text_fn},
            tag_click_fn: ${tag_click_fn},
            ajax_autocomplete_tag_url: "${h.url_for( controller='tag', action='tag_autocomplete_data', id=tagged_item_id, item_class=tagged_item.__class__.__name__ )}",
            ajax_add_tag_url: "${h.url_for( controller='tag', action='add_tag_async', id=tagged_item_id, item_class=tagged_item.__class__.__name__, context=elt_context )}",
            ajax_delete_tag_url: "${h.url_for( controller='tag', action='remove_tag_async', id=tagged_item_id, item_class=tagged_item.__class__.__name__, context=elt_context )}",
            delete_tag_img: "${h.url_for('/static/images/delete_tag_icon_gray.png')}",
            delete_tag_img_rollover: "${h.url_for('/static/images/delete_tag_icon_white.png')}",
            use_toggle_link: ${iff( use_toggle_link, 'true', 'false' )},
         };
         
        $("#${elt_id}").autocomplete_tagging('${elt_id}', options);
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