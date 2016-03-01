// This is an extension to jQuery UI draggable
// When dragging move the parent element ("panel") relative to its parent
// ("viewport") so that the draggable is always visible. 

$.ui.plugin.add("draggable", "scrollPanel", {
    drag: function(e, ui) {
        var instance = $(this).data("draggable");
        clearTimeout( instance.timeout );
        var o = ui.options,
            element = instance.element,
            panel = o.panel,
            panel_pos = panel.position(),
            panel_w = panel.width(),
            panel_h = panel.height()
            viewport = panel.parent();
            viewport_w = viewport.width(),
            viewport_h = viewport.height(),
            element_w = element.width(),
            element_h = element.height(),
            moved = false,
            close_dist = 5,
            nudge = 23,
            // Legal panel range
            p_min_x = - ( panel_w - viewport_w ),
            p_min_y = - ( panel_h - viewport_h ),
            p_max_x = 0,
            p_max_y = 0,
            // Visible
            min_vis_x = - panel_pos.left,
            max_vis_x = min_vis_x + viewport_w,
            min_vis_y = - panel_pos.top,
            max_vis_y = min_vis_y + viewport_h,
            // Mouse
            mouse_x = ui.position.left + instance.offset.click.left;
            mouse_y = ui.position.top + instance.offset.click.top;
        // Move it
        if ( ( panel_pos.left < p_max_x ) && ( mouse_x - close_dist < min_vis_x ) ) {
            var t = Math.min( nudge, p_max_x - panel_pos.left );
            panel.css( "left", panel_pos.left + t );
            moved = true;
            instance.offset.parent.left += t;
            ui.position.left -= t
        }
        if ( ( ! moved ) && ( panel_pos.left > p_min_x ) && ( mouse_x + close_dist > max_vis_x ) ) {
            var t = Math.min( nudge, panel_pos.left  - p_min_x );
            panel.css( "left", panel_pos.left - t );
            moved = true;
            instance.offset.parent.left -= t;
            ui.position.left += t;      
        }
        if ( ( ! moved ) && ( panel_pos.top < p_max_y ) && ( mouse_y - close_dist < min_vis_y ) ) {
            var t = Math.min( nudge, p_max_y - panel_pos.top );
            panel.css( "top", panel_pos.top + t );
            // Firefox sometimes moves by less, so we need to check. Yuck.
            var amount_moved = panel.position().top - panel_pos.top;
            instance.offset.parent.top += amount_moved;
            ui.position.top -= amount_moved;
            moved = true;
        }
        if ( ( ! moved ) && ( panel_pos.top > p_min_y ) && ( mouse_y + close_dist > max_vis_y ) ) {
            var t = Math.min( nudge, panel_pos.top  - p_min_x );
            panel.css( "top", ( panel_pos.top - t ) + "px" );
            // Firefox sometimes moves by less, so we need to check. Yuck.
            var amount_moved = panel_pos.top - panel.position().top;   
            instance.offset.parent.top -= amount_moved;
            ui.position.top += amount_moved;
            moved = true;
        }
        // Still contain in panel
        ui.position.left = Math.max( ui.position.left, 0 );
        ui.position.top = Math.max( ui.position.top, 0 );
        ui.position.left = Math.min( ui.position.left, panel_w - element_w );
        ui.position.top = Math.min( ui.position.top, panel_h - element_h );
        // Update offsets
        if ( moved ) {
            $.ui.ddmanager.prepareOffsets( instance, e );
        }
        // Keep moving even if mouse doesn't move
        if ( moved ) {
            instance.old_e = e;
            instance.timeout = setTimeout( function() { instance.mouseMove( e ) }, 50 );
        }
    },
    stop: function( e, ui ) {
        var instance = $(this).data("draggable");
        clearTimeout( instance.timeout );
    }
});