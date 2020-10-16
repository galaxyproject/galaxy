import jQuery from "jquery";
("use_strict");

var $ = jQuery;
// ============================================================================
/**
 * Edit and save text asynchronously.
 */
function async_save_text(
    click_to_edit_elt,
    text_elt_id,
    save_url,
    text_parm_name,
    num_cols,
    use_textarea,
    num_rows,
    on_start,
    on_finish
) {
    // Set defaults if necessary.
    if (num_cols === undefined) {
        num_cols = 30;
    }
    if (num_rows === undefined) {
        num_rows = 4;
    }

    // Set up input element.
    $(`#${click_to_edit_elt}`)
        .off()
        .click(() => {
            // Check if this is already active
            if ($("#renaming-active").length > 0) {
                return;
            }
            var text_elt = $(`#${text_elt_id}`);
            var old_text = text_elt.text();
            var t;

            if (use_textarea) {
                t = $("<textarea></textarea>")
                    .attr({ rows: num_rows, cols: num_cols })
                    .text($.trim(old_text));
            } else {
                t = $("<input type='text'></input>").attr({
                    value: $.trim(old_text),
                    size: num_cols
                });
            }
            t.attr("id", "renaming-active");
            t.blur(function() {
                $(this).remove();
                text_elt.show();
                if (on_finish) {
                    on_finish(t);
                }
            });
            t.keyup(function(e) {
                if (e.keyCode === 27) {
                    // Escape key
                    $(this).trigger("blur");
                } else if (e.keyCode === 13) {
                    // Enter key submits
                    var ajax_data = {};
                    ajax_data[text_parm_name] = $(this).val();
                    $(this).trigger("blur");
                    $.ajax({
                        url: save_url,
                        data: ajax_data,
                        error: function() {
                            alert(`Text editing for elt ${text_elt_id} failed`);
                            // TODO: call finish or no? For now, let's not because error occurred.
                        },
                        success: function(processed_text) {
                            // Set new text and call finish method.
                            if (processed_text !== "") {
                                text_elt.text(processed_text);
                            } else {
                                text_elt.html("<em>None</em>");
                            }
                            if (on_finish) {
                                on_finish(t);
                            }
                        }
                    });
                }
            });

            if (on_start) {
                on_start(t);
            }
            // Replace text with input object and focus & select.
            text_elt.hide();
            t.insertAfter(text_elt);
            t.focus();
            t.select();

            return;
        });
}

// ============================================================================
export default async_save_text;
