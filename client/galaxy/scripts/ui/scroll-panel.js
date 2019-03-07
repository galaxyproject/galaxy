import $ from "jquery";

// This is an extension to jQuery UI draggable
// When dragging move the parent element ("panel") relative to its parent
// ("viewport") so that the draggable is always visible.

$.ui.plugin.add("draggable", "scrollPanel", {
    drag: function(e, ui) {
        var instance = $(this).data("draggable");
        clearTimeout(instance.timeout);
        var o = ui.options;
        var element = instance.element;
        var panel = o.panel;
        var panel_pos = panel.position();
        var panel_w = panel.width();
        var panel_h = panel.height();
        var viewport = panel.parent();
        var viewport_w = viewport.width();
        var viewport_h = viewport.height();
        var element_w = element.width();
        var element_h = element.height();
        var moved = false;
        var close_dist = 5;
        var nudge = 23;

        var // Legal panel range
            p_min_x = -(panel_w - viewport_w);

        var p_min_y = -(panel_h - viewport_h);
        var p_max_x = 0;
        var p_max_y = 0;

        var // Visible
            min_vis_x = -panel_pos.left;

        var max_vis_x = min_vis_x + viewport_w;
        var min_vis_y = -panel_pos.top;
        var max_vis_y = min_vis_y + viewport_h;

        // Mouse
        var mouse_x = ui.position.left + instance.offset.click.left;
        var mouse_y = ui.position.top + instance.offset.click.top;

        // Move it
        if (panel_pos.left < p_max_x && mouse_x - close_dist < min_vis_x) {
            let t = Math.min(nudge, p_max_x - panel_pos.left);
            panel.css("left", panel_pos.left + t);
            moved = true;
            instance.offset.parent.left += t;
            ui.position.left -= t;
        }
        if (!moved && panel_pos.left > p_min_x && mouse_x + close_dist > max_vis_x) {
            let t = Math.min(nudge, panel_pos.left - p_min_x);
            panel.css("left", panel_pos.left - t);
            moved = true;
            instance.offset.parent.left -= t;
            ui.position.left += t;
        }
        if (!moved && panel_pos.top < p_max_y && mouse_y - close_dist < min_vis_y) {
            let t = Math.min(nudge, p_max_y - panel_pos.top);
            panel.css("top", panel_pos.top + t);
            // Firefox sometimes moves by less, so we need to check. Yuck.
            let amount_moved = panel.position().top - panel_pos.top;
            instance.offset.parent.top += amount_moved;
            ui.position.top -= amount_moved;
            moved = true;
        }
        if (!moved && panel_pos.top > p_min_y && mouse_y + close_dist > max_vis_y) {
            var t = Math.min(nudge, panel_pos.top - p_min_x);
            panel.css("top", `${panel_pos.top - t}px`);
            // Firefox sometimes moves by less, so we need to check. Yuck.
            let amount_moved = panel_pos.top - panel.position().top;
            instance.offset.parent.top -= amount_moved;
            ui.position.top += amount_moved;
            moved = true;
        }
        // Still contain in panel
        ui.position.left = Math.max(ui.position.left, 0);
        ui.position.top = Math.max(ui.position.top, 0);
        ui.position.left = Math.min(ui.position.left, panel_w - element_w);
        ui.position.top = Math.min(ui.position.top, panel_h - element_h);
        // Update offsets
        if (moved) {
            $.ui.ddmanager.prepareOffsets(instance, e);
        }
        // Keep moving even if mouse doesn't move
        if (moved) {
            instance.old_e = e;
            instance.timeout = setTimeout(() => {
                instance.mouseMove(e);
            }, 50);
        }
    },
    stop: function(e, ui) {
        var instance = $(this).data("draggable");
        clearTimeout(instance.timeout);
    }
});
