// from: https://raw.githubusercontent.com/umdjs/umd/master/jqueryPlugin.js
// Uses AMD or browser globals to create a jQuery plugin.
(function (factory) {
    if (typeof define === 'function' && define.amd) {
        //TODO: So...this turns out to be an all or nothing thing. If I load jQuery in the define below, it will
        //  (of course) wipe the old jquery *and all the plugins loaded into it*. So the define below *is still
        //  relying on jquery being loaded globally* in order to preserve plugins.
        define([ 'jquery' ], factory);
    } else {
        // Browser globals
        factory(jQuery);
    }

}(function ( jQuery ) {
'use_strict';

var $ = jQuery;

// ============================================================================
/**
* JQuery extension for tagging with autocomplete.
* @author: Jeremy Goecks
* @require: jquery.autocomplete plugin
*/
//
// Initialize "tag click functions" for tags.
//
function init_tag_click_function(tag_elt, click_func) {
    $(tag_elt).find('.tag-name').each( function() {
        $(this).click( function() {
            var tag_str = $(this).text();
            var tag_name_and_value = tag_str.split(":");
            click_func(tag_name_and_value[0], tag_name_and_value[1]);
            return true;
        });
    });
}

jQuery.fn.autocomplete_tagging = function(options) {

    var defaults = {
        get_toggle_link_text_fn: function(tags) {
            var text = "";
            var num_tags = _.size(tags);
            if (num_tags > 0) {
                text = num_tags + (num_tags > 1 ? " Tags" : " Tag");
            } else {
                text = "Add tags";
            }
            return text;
        },
        tag_click_fn : function (name, value) {},
        editable: true,
        input_size: 20,
        in_form: false,
        tags : {},
        use_toggle_link: true,
        item_id: "",
        add_tag_img: "",
        add_tag_img_rollover: "",
        delete_tag_img: "",
        ajax_autocomplete_tag_url: "",
        ajax_retag_url: "",
        ajax_delete_tag_url: "",
        ajax_add_tag_url: ""
    };

    var settings = jQuery.extend(defaults, options);

    //
    // Initalize object's elements.
    //

    // Get elements for this object. For this_obj, assume the last element with the id is the "this"; this is somewhat of a hack to address the problem
    // that there may be two tagging elements for a single item if there are both community and individual tags for an element.
    var this_obj = $(this);
    var tag_area = this_obj.find('.tag-area');
    var toggle_link = this_obj.find('.toggle-link');
    var tag_input_field = this_obj.find('.tag-input');
    var add_tag_button = this_obj.find('.add-tag-button');

    // Initialize toggle link.
    toggle_link.click( function() {
        // Take special actions depending on whether toggle is showing or hiding link.
        var after_toggle_fn;
        if (tag_area.is(":hidden")) {
            after_toggle_fn = function() {
                // If there are no tags, go right to editing mode by generating a click on the area.
                var num_tags = $(this).find('.tag-button').length;
                if (num_tags === 0) {
                    tag_area.click();
                }
            };
        } else {
            after_toggle_fn = function() {
                tag_area.blur();
            };
        }
        tag_area.slideToggle("fast", after_toggle_fn);
        return $(this);
    });

    // Initialize tag input field.
    if (settings.editable) {
        tag_input_field.hide();
    }
    tag_input_field.keyup( function(e) {
        if ( e.keyCode === 27 ) {
            // Escape key
            $(this).trigger( "blur" );
        } else if (
            ( e.keyCode === 13 ) || // Return Key
            ( e.keyCode === 188 ) || // Comma
            ( e.keyCode === 32 ) // Space
        ) {
            //
            // Check input.
            //

            var new_value = this.value;

            // Suppress space after a ":"
            if ( new_value.indexOf(": ", new_value.length - 2) !== -1) {
                this.value = new_value.substring(0, new_value.length-1);
                return false;
            }

            // Remove trigger keys from input.
            if ( (e.keyCode === 188) || (e.keyCode === 32) ) {
                new_value = new_value.substring( 0 , new_value.length - 1 );
            }

            // Trim whitespace.
            new_value = $.trim(new_value);

            // Too short?
            if (new_value.length < 2) {
                return false;
            }

            //
            // New tag OK - apply it.
            //

            this.value = ""; // Reset text field now that tag is being added

            // Add button for tag after all other tag buttons.
            var new_tag_button = build_tag_button(new_value);
            var tag_buttons = tag_area.children(".tag-button");
            if (tag_buttons.length !== 0) {
                var last_tag_button = tag_buttons.slice(tag_buttons.length-1);
                last_tag_button.after(new_tag_button);
            } else {
                tag_area.prepend(new_tag_button);
            }

            // Add tag to internal list.
            var tag_name_and_value = new_value.split(":");
            settings.tags[tag_name_and_value[0]] = tag_name_and_value[1];

            // Update toggle link text.
            var new_text = settings.get_toggle_link_text_fn(settings.tags);
            toggle_link.text(new_text);

            // Commit tag to server.
            var zz = $(this);
            $.ajax({
                url: settings.ajax_add_tag_url,
                data: { new_tag: new_value },
                error: function() {
                    // Failed. Roll back changes and show alert.
                    new_tag_button.remove();
                    delete settings.tags[tag_name_and_value[0]];
                    var new_text = settings.get_toggle_link_text_fn(settings.tags);
                    toggle_link.text(new_text);
                    alert( "Add tag failed" );
                },
                success: function() {
                    // Flush autocomplete cache because it's not out of date.
                    // TODO: in the future, we could remove the particular item
                    // that was chosen from the cache rather than flush it.
                    zz.data('autocompleter').cacheFlush();
                }
            });

            return false;
        }
    });

    // Add autocomplete to input.
    var format_item_func = function(key, row_position, num_rows, value, search_term) {
        var tag_name_and_value = value.split(":");
        return (tag_name_and_value.length === 1 ? tag_name_and_value[0] : tag_name_and_value[1]);
    };
    var autocomplete_options = { selectFirst: false, formatItem: format_item_func,
            autoFill: false, highlight: false };
    tag_input_field.autocomplete_verheul(settings.ajax_autocomplete_tag_url, autocomplete_options);


    // Initialize delete tag images for current tags.
    this_obj.find('.delete-tag-img').each(function() {
        init_delete_tag_image( $(this) );
    });


    // Initialize tag click function.
    init_tag_click_function($(this), settings.tag_click_fn);

    // Initialize "add tag" button.
    add_tag_button.click( function() {
        $(this).hide();

        // Clicking on button is the same as clicking on the tag area.
        tag_area.click();
        return false;
    });

    //
    // Set up tag area interactions; these are needed only if tags are editable.
    //
    if (settings.editable) {
        // When the tag area blurs, go to "view tag" mode.
        tag_area.bind("blur", function(e) {
            if (_.size(settings.tags) > 0) {
                add_tag_button.show();
                tag_input_field.hide();
                tag_area.removeClass("active-tag-area");
                // tag_area.addClass("tooltip");
            } else {
                // No tags, so do nothing to ensure that input is still visible.
            }
        });

        // On click, enable user to add tags.
        tag_area.click( function(e) {
            var is_active = $(this).hasClass("active-tag-area");

            // If a "delete image" object was pressed and area is inactive, do nothing.
            if ($(e.target).hasClass("delete-tag-img") && !is_active) {
                return false;
            }

            // If a "tag name" object was pressed and area is inactive, do nothing.
            if ($(e.target).hasClass("tag-name") && !is_active) {
                return false;
            }

            // Remove tooltip.
            // $(this).removeClass("tooltip");

            // Hide add tag button, show tag_input field. Change background to show
            // area is active.
            $(this).addClass("active-tag-area");
            add_tag_button.hide();
            tag_input_field.show();
            tag_input_field.focus();

            // Add handler to document that will call blur when the tag area is blurred;
            // a tag area is blurred when a user clicks on an element outside the area.
            var handle_document_click = function(e)  {
                var check_click = function(tag_area, target) {
                    var tag_area_id = tag_area.attr("id");
                    // Blur the tag area if the element clicked on is not in the tag area.
                    if (target !== tag_area) {
                        tag_area.blur();
                        $(window).unbind("click.tagging_blur");
                        $(this).addClass("tooltip");
                    }
                };
                check_click(tag_area, $(e.target));
            };
            // TODO: we should attach the click handler to all frames in order to capture
            // clicks outside the frame that this element is in.
            //window.parent.document.onclick = handle_document_click;
            //var temp = $(window.parent.document.body).contents().find("iframe").html();
            //alert(temp);
            //$(document).parent().click(handle_document_click);
            $(window).bind("click.tagging_blur", handle_document_click);

            return false;
        });
    }

    // If using toggle link, hide the tag area. Otherwise, show the tag area.
    if (settings.use_toggle_link) {
        tag_area.hide();
    }

    //
    // Helper functions.
    //

    //
    // Collapse tag name + value into a single string.
    //
    function build_tag_str(tag_name, tag_value) {
        return tag_name + ( tag_value ? ":" + tag_value : "");
    }


    // Initialize a "delete tag image": when click, delete tag from UI and send delete request to server.
    function init_delete_tag_image(delete_img) {
        $(delete_img).mouseenter( function () {
            $(this).attr("src", settings.delete_tag_img_rollover);
        });
        $(delete_img).mouseleave( function () {
            $(this).attr("src", settings.delete_tag_img);
        });
        $(delete_img).click( function () {
            // Tag button is image's parent.
            var tag_button = $(this).parent();

            // Get tag name, value.
            var tag_name_elt = tag_button.find(".tag-name").eq(0);
            var tag_str = tag_name_elt.text();
            var tag_name_and_value = tag_str.split(":");
            var tag_name = tag_name_and_value[0];
            var tag_value = tag_name_and_value[1];

            var prev_button = tag_button.prev();
            tag_button.remove();

            // Remove tag from local list for consistency.
            delete settings.tags[tag_name];

            // Update toggle link text.
            var new_text = settings.get_toggle_link_text_fn(settings.tags);
            toggle_link.text(new_text);

            // Delete tag.
            $.ajax({
                url: settings.ajax_delete_tag_url,
                data: { tag_name: tag_name },
                error: function() {
                    // Failed. Roll back changes and show alert.
                    settings.tags[tag_name] = tag_value;
                    if (prev_button.hasClass("tag-button")) {
                        prev_button.after(tag_button);
                    } else {
                        tag_area.prepend(tag_button);
                    }
                    alert( "Remove tag failed" );

                    toggle_link.text(settings.get_toggle_link_text_fn(settings.tags));

                    // TODO: no idea why it's necessary to set this up again.
                    delete_img.mouseenter( function () {
                        $(this).attr("src", settings.delete_tag_img_rollover);
                    });
                    delete_img.mouseleave( function () {
                        $(this).attr("src", settings.delete_tag_img);
                    });
                },
                success: function() {}
            });

            return true;
        });
    }

    //
    // Function that builds a tag button.
    //
    function build_tag_button(tag_str) {
        // Build "delete tag" image.
        var delete_img = $("<img/>").attr("src", settings.delete_tag_img).addClass("delete-tag-img");
        init_delete_tag_image(delete_img);

        // Build tag button.
        var tag_name_elt = $("<span>").text(tag_str).addClass("tag-name");
        tag_name_elt.click( function() {
            var tag_name_and_value = tag_str.split(":");
            settings.tag_click_fn(tag_name_and_value[0], tag_name_and_value[1]);
            return true;
        });

        var tag_button = $("<span></span>").addClass("tag-button");
        tag_button.append(tag_name_elt);
        // Allow delete only if element is editable.
        if (settings.editable) {
            tag_button.append(delete_img);
        }

        return tag_button;
    }

};

// ============================================================================
    return init_tag_click_function;
}));
