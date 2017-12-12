define("mvc/workflow/workflow-connector", ["exports"], function(exports) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    function Connector(handle1, handle2) {
        this.canvas = null;
        this.dragging = false;
        this.inner_color = "#FFFFFF";
        this.outer_color = "#D8B365";
        if (handle1 && handle2) {
            this.connect(handle1, handle2);
        }
    }
    $.extend(Connector.prototype, {
        connect: function connect(t1, t2) {
            this.handle1 = t1;
            if (this.handle1) {
                this.handle1.connect(this);
            }
            this.handle2 = t2;
            if (this.handle2) {
                this.handle2.connect(this);
            }
        },
        destroy: function destroy() {
            if (this.handle1) {
                this.handle1.disconnect(this);
            }
            if (this.handle2) {
                this.handle2.disconnect(this);
            }
            $(this.canvas).remove();
        },
        destroyIfInvalid: function destroyIfInvalid() {
            if (this.handle1 && this.handle2 && !this.handle2.attachable(this.handle1)) {
                this.destroy();
            }
        },
        redraw: function redraw() {
            var canvas_container = $("#canvas-container");
            if (!this.canvas) {
                this.canvas = document.createElement("canvas");
                canvas_container.append($(this.canvas));
                if (this.dragging) {
                    this.canvas.style.zIndex = "300";
                }
            }
            var relativeLeft = function relativeLeft(e) {
                return $(e).offset().left - canvas_container.offset().left;
            };
            var relativeTop = function relativeTop(e) {
                return $(e).offset().top - canvas_container.offset().top;
            };
            if (!this.handle1 || !this.handle2) {
                return;
            }
            // Find the position of each handle
            var start_x = relativeLeft(this.handle1.element) + 5;
            var start_y = relativeTop(this.handle1.element) + 5;
            var end_x = relativeLeft(this.handle2.element) + 5;
            var end_y = relativeTop(this.handle2.element) + 5;
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
            this.canvas.style.left = canvas_left + "px";
            this.canvas.style.top = canvas_top + "px";
            this.canvas.setAttribute("width", canvas_width);
            this.canvas.setAttribute("height", canvas_height);
            // Adjust points to be relative to the canvas
            start_x -= canvas_left;
            start_y -= canvas_top;
            end_x -= canvas_left;
            end_y -= canvas_top;

            // Draw the line

            var c = this.canvas.getContext("2d");

            var start_offsets = null;
            var end_offsets = null;
            var num_offsets = 1;
            if (this.handle1 && this.handle1.isMappedOver()) {
                var start_offsets = [-6, -3, 0, 3, 6];
                num_offsets = 5;
            } else {
                var start_offsets = [0];
            }
            if (this.handle2 && this.handle2.isMappedOver()) {
                var end_offsets = [-6, -3, 0, 3, 6];
                num_offsets = 5;
            } else {
                var end_offsets = [0];
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
                connector.draw_outlined_curve(start_x, start_y, end_x, end_y, cp_shift, inner_width, outer_width, start_offsets[i % start_offsets.length], end_offsets[i % end_offsets.length]);
            }
        },
        draw_outlined_curve: function draw_outlined_curve(start_x, start_y, end_x, end_y, cp_shift, inner_width, outer_width, offset_start, offset_end) {
            var offset_start = offset_start || 0;
            var offset_end = offset_end || 0;
            var c = this.canvas.getContext("2d");
            c.lineCap = "round";
            c.strokeStyle = this.outer_color;
            c.lineWidth = outer_width;
            c.beginPath();
            c.moveTo(start_x, start_y + offset_start);
            c.bezierCurveTo(start_x + cp_shift, start_y + offset_start, end_x - cp_shift, end_y + offset_end, end_x, end_y + offset_end);
            c.stroke();
            // Inner line
            c.strokeStyle = this.inner_color;
            c.lineWidth = inner_width;
            c.beginPath();
            c.moveTo(start_x, start_y + offset_start);
            c.bezierCurveTo(start_x + cp_shift, start_y + offset_start, end_x - cp_shift, end_y + offset_end, end_x, end_y + offset_end);
            c.stroke();
        }
    });
    exports.default = Connector;
});
//# sourceMappingURL=../../../maps/mvc/workflow/workflow-connector.js.map
