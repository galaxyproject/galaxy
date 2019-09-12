import jQuery from "jquery";
("use_strict");

var $ = jQuery;

// ============================================================================
/**
 * Make an element with text editable: (a) when user clicks on text, a textbox/area
 * is provided for editing; (b) when enter key pressed, element's text is set and on_finish
 * is called.
 */
$.fn.make_text_editable = function(config_dict) {
    // Get config options.
    var num_cols = "num_cols" in config_dict ? config_dict.num_cols : 30;

    var num_rows = "num_rows" in config_dict ? config_dict.num_rows : 4;

    var use_textarea = "use_textarea" in config_dict ? config_dict.use_textarea : false;

    var on_finish = "on_finish" in config_dict ? config_dict.on_finish : null;
    var help_text = "help_text" in config_dict ? config_dict.help_text : null;

    // Add element behavior.
    var container = $(this);
    container.addClass("editable-text").click(function(e) {
        // If there's already an input element, editing is active, so do nothing.
        if ($(this).children(":input").length > 0) {
            return;
        }

        container.removeClass("editable-text");

        // Handler for setting element text.
        var set_text = new_text => {
            container.find(":input").remove();

            if (new_text !== "") {
                container.text(new_text);
            } else {
                // No text; need a line so that there is a click target.
                container.html("<br>");
            }
            container.addClass("editable-text");

            if (on_finish) {
                on_finish(new_text);
            }
        };

        // Create input element(s) for editing.
        var cur_text = "cur_text" in config_dict ? config_dict.cur_text : container.text();

        var input_elt;
        var button_elt;

        if (use_textarea) {
            input_elt = $("<textarea/>")
                .attr({ rows: num_rows, cols: num_cols })
                .text($.trim(cur_text))
                .keyup(e => {
                    if (e.keyCode === 27) {
                        // Escape key.
                        set_text(cur_text);
                    }
                });
            button_elt = $("<button/>")
                .addClass("btn-sm float-right")
                .text("Done")
                .click(() => {
                    set_text(input_elt.val());
                    // Return false so that click does not propogate to container.
                    return false;
                });
        } else {
            input_elt = $("<input type='text'/>")
                .attr({ value: $.trim(cur_text), size: num_cols })
                .blur(() => {
                    set_text(cur_text);
                })
                .keyup(function(e) {
                    if (e.keyCode === 27) {
                        // Escape key.
                        $(this).trigger("blur");
                    } else if (e.keyCode === 13) {
                        // Enter key.
                        set_text($(this).val());
                    }

                    // Do not propogate event to avoid unwanted side effects.
                    e.stopPropagation();
                });
        }

        // Replace text with input object(s) and focus & select.
        container.text("");
        container.append(input_elt);
        if (button_elt) {
            container.append(button_elt);
        }
        input_elt.focus();
        input_elt.select();

        // Do not propogate to elements below b/c that blurs input and prevents it from being used.
        e.stopPropagation();
    });

    // Add help text if there some.
    if (help_text) {
        container.attr("title", help_text).tooltip();
    }

    return container;
};

// ============================================================================
