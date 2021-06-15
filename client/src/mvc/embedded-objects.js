import $ from "jquery";
import { make_popup_menus } from "ui/popupmenu";

export function render_embedded_items() {
    $(".embedded-item").each(function () {
        var container = $(this);
        if (container.hasClass("history")) {
            return;
        }
        //note: we can't do the same override for visualizations
        // bc builtins (like trackster) need the handlers/ajax below to work.
        // instead: (for registry visualizations) we'll clear the handlers below
        //  and add new ones (in embed_in_frame.mako) ...ugh.

        // Show embedded item.
        var show_embedded_item = function () {
            var ajax_url = container.find("input[type=hidden]").val();
            if (!ajax_url) {
                ajax_url = container.data("item-url");
            }
            // Only get item content if it's not already there.
            var item_content = $.trim(container.find(".item-content").text());
            if (!item_content) {
                $.ajax({
                    type: "GET",
                    url: ajax_url,
                    error: function () {
                        alert("Getting item content failed.");
                    },
                    success: function (item_content) {
                        container.find(".summary-content").hide("fast");
                        container.find(".item-content").html(item_content);
                        container.find(".expanded-content").show("fast");
                        container.find(".toggle-expand").hide();
                        container.find(".toggle").show();

                        make_popup_menus();
                    },
                });
            } else {
                container.find(".summary-content").hide("fast");
                container.find(".expanded-content").show("fast");
                container.find(".toggle-expand").hide();
                container.find(".toggle").show();
            }
        };

        // Hide embedded item.
        var hide_embedded_item = function () {
            container.find(".expanded-content").hide("fast");
            container.find(".summary-content").show("fast");
            container.find(".toggle").hide();
            container.find(".toggle-expand").show();
        };

        // Setup toggle expand.
        var toggle_expand = $(this).find(".toggle-expand");
        toggle_expand.click(function () {
            show_embedded_item();
            return false;
        });
        // Setup toggle contract.
        var toggle_contract = $(this).find(".toggle");
        toggle_contract.click(function () {
            hide_embedded_item();
            return false;
        });

        // Setup toggle embed.
        var toggle_embed = $(this).find(".toggle-embed");
        toggle_embed.click(function () {
            if (container.find(".expanded-content").is(":visible")) {
                hide_embedded_item();
            } else {
                show_embedded_item();
            }
            return false;
        });
        if ($(this).hasClass("expanded")) {
            show_embedded_item();
        }
    });
}
