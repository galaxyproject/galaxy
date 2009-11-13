## Render a tagging element if there is a tagged_item.
%if tagged_item is not None and elt_id is not None:
    ${render_tagging_element(tagged_item, elt_id=elt_id, in_form=in_form, input_size=input_size, tag_click_fn=tag_click_fn)}
%endif

## Render the tags 'tags' as an autocomplete element.
<%def name="render_tagging_element(tagged_item, elt_id, use_toggle_link='true', in_form='false', input_size='15', tag_click_fn='default_tag_click_fn', get_toggle_link_text_fn='default_get_toggle_link_text_fn', editable='true')">
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
            editable : ${str(editable).lower()},
            get_toggle_link_text_fn: ${get_toggle_link_text_fn},
            tag_click_fn: ${tag_click_fn},
            <% tagged_item_id = trans.security.encode_id(tagged_item.id) %>
            ajax_autocomplete_tag_url: "${h.url_for( controller='tag', action='tag_autocomplete_data', id=tagged_item_id, item_class=tagged_item.__class__.__name__ )}",
            ajax_add_tag_url: "${h.url_for( controller='tag', action='add_tag_async', id=tagged_item_id, item_class=tagged_item.__class__.__name__ )}",
            ajax_delete_tag_url: "${h.url_for( controller='tag', action='remove_tag_async', id=tagged_item_id, item_class=tagged_item.__class__.__name__ )}",
            delete_tag_img: "${h.url_for('/static/images/delete_tag_icon_gray.png')}",
            delete_tag_img_rollover: "${h.url_for('/static/images/delete_tag_icon_white.png')}",
            add_tag_img: "${h.url_for('/static/images/add_icon.png')}",
            add_tag_img_rollover: "${h.url_for('/static/images/add_icon_dark.png')}",
            input_size: ${input_size},
            in_form: ${in_form},
            use_toggle_link: ${use_toggle_link}
         };
         
        $("#${elt_id}").autocomplete_tagging(options)
    </script>
</%def>