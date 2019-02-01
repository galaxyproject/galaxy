import $ from "jquery";

import * as Toastr from "libs/toastr";

function Connector(handle1, handle2) {
    this.canvas = null;
    this.dragging = false;
    this.inner_color = "#FFFFFF";
    this.outer_color = "#25537b";
    if (handle1 && handle2) {
        this.connect(
            handle1,
            handle2
        );
    }
}
$.extend(Connector.prototype, {
    connect: function(t1, t2) {
        this.handle1 = t1;
        if (this.handle1) {
            this.handle1.connect(this);
        }
        this.handle2 = t2;
        if (this.handle2) {
            this.handle2.connect(this);
        }
    },
    destroy: function() {
        if (this.handle1) {
            this.handle1.disconnect(this);
        }
        if (this.handle2) {
            this.handle2.disconnect(this);
        }
        $(this.canvas).remove();
    },
    destroyIfInvalid: function(warn) {
        if (this.handle1 && this.handle2 && !this.handle2.attachable(this.handle1)) {
            if (warn) {
                Toastr.warning("Destroying a connection because collection type has changed.");
            }
            this.destroy();
        }
    },
    redraw: function() {
        const handle1 = this.handle1;
        const handle2 = this.handle2;
        const startRibbon = handle1 && handle1.isMappedOver();
        const endRibbon = handle2 && handle2.isMappedOver();
        const canvasClass = `${startRibbon ? "start-ribbon" : ""} ${endRibbon ? "end-ribbon" : ""}`;
        var canvas_container = $("#canvas-container");
        // FIXME: global
        var canvasZoom = window.workflow_globals.canvas_manager.canvasZoom;
        if (!this.canvas) {
            this.canvas = document.createElement("canvas");
            canvas_container.append($(this.canvas));
            if (this.dragging) {
                this.canvas.style.zIndex = "300";
            }
        }
        this.canvas.setAttribute(
            "handle1-id",
            handle1 && handle1.element.getAttribute ? handle1.element.getAttribute("id") : ""
        );
        this.canvas.setAttribute(
            "handle2-id",
            handle2 && handle2.element.getAttribute ? handle2.element.getAttribute("id") : ""
        );
        var relativeLeft = e => ($(e).offset().left - canvas_container.offset().left) / canvasZoom;
        var relativeTop = e => ($(e).offset().top - canvas_container.offset().top) / canvasZoom;
        if (!handle1 || !handle2) {
            return;
        }
        // Find the position of each handle
        var start_x = relativeLeft(handle1.element) + 5;
        var start_y = relativeTop(handle1.element) + 5;
        var end_x = relativeLeft(handle2.element) + 5;
        var end_y = relativeTop(handle2.element) + 5;
        // Calculate canvas area
        var canvas_extra = 100;
        var canvas_min_x = Math.min(start_x, end_x);
        var canvas_max_x = Math.max(start_x, end_x);
        var canvas_min_y = Math.min(start_y, end_y);
        var canvas_max_y = Math.max(start_y, end_y);
        var cp_shift = Math.min(Math.max(Math.abs(canvas_max_y - canvas_min_y) / 2, 100), 300);
        var canvas_left = canvas_min_x - canvas_extra;
        var canvas_top = canvas_min_y - canvas_extra;
        var canvas_width = canvas_max_x - canvas_min_x + 2 * canvas_extra;
        var canvas_height = canvas_max_y - canvas_min_y + 2 * canvas_extra;
        // Place the canvas
        this.canvas.style.left = `${canvas_left}px`;
        this.canvas.style.top = `${canvas_top}px`;
        this.canvas.setAttribute("width", canvas_width);
        this.canvas.setAttribute("height", canvas_height);
        this.canvas.setAttribute("class", canvasClass);
        // Adjust points to be relative to the canvas
        start_x -= canvas_left;
        start_y -= canvas_top;
        end_x -= canvas_left;
        end_y -= canvas_top;

        // Draw the line

        var start_offsets = null;
        var end_offsets = null;
        var num_offsets = 1;
        if (startRibbon) {
            start_offsets = [-6, -3, 0, 3, 6];
            num_offsets = 5;
        } else {
            start_offsets = [0];
        }
        if (endRibbon) {
            end_offsets = [-6, -3, 0, 3, 6];
            num_offsets = 5;
        } else {
            end_offsets = [0];
        }
        var connector = this;
        for (var i = 0; i < num_offsets; i++) {
            var inner_width = 5;
            var outer_width = 7;
            if (start_offsets.length > 1 || end_offsets.length > 1) {
                // We have a multi-run, using many lines, make them small.
                inner_width = 1;
                outer_width = 3;
            }
            connector.draw_outlined_curve(
                start_x,
                start_y,
                end_x,
                end_y,
                cp_shift,
                inner_width,
                outer_width,
                start_offsets[i % start_offsets.length],
                end_offsets[i % end_offsets.length]
            );
        }
    },
    draw_outlined_curve: function(
        start_x,
        start_y,
        end_x,
        end_y,
        cp_shift,
        inner_width,
        outer_width,
        offset_start,
        offset_end
    ) {
        var c = this.canvas.getContext("2d");
        offset_start = offset_start || 0;
        offset_end = offset_end || 0;
        c.lineCap = "round";
        c.strokeStyle = this.outer_color;
        c.lineWidth = outer_width;
        c.beginPath();
        c.moveTo(start_x, start_y + offset_start);
        c.bezierCurveTo(
            start_x + cp_shift,
            start_y + offset_start,
            end_x - cp_shift,
            end_y + offset_end,
            end_x,
            end_y + offset_end
        );
        c.stroke();
        // Inner line
        c.strokeStyle = this.inner_color;
        c.lineWidth = inner_width;
        c.beginPath();
        c.moveTo(start_x, start_y + offset_start);
        c.bezierCurveTo(
            start_x + cp_shift,
            start_y + offset_start,
            end_x - cp_shift,
            end_y + offset_end,
            end_x,
            end_y + offset_end
        );
        c.stroke();
    }
});
export default Connector;
