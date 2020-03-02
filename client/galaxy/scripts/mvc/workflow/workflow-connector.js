import $ from "jquery";
import * as d3 from "d3";
import { Toast } from "ui/toast";

function Connector(manager) {
    this.manager = manager;
    this.dragging = false;
    this.inner_color = "#FFFFFF";
    this.outer_color = "#25537b";
    this.canvas = document.createElement("div");
    this.canvas.style.position = "absolute";
    const container = document.getElementById("canvas-container");
    container.appendChild(this.canvas);
    this.svg = d3.select(this.canvas).append("svg");
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
        this.canvas.remove();
    },
    destroyIfInvalid: function(warn) {
        if (this.handle1 && this.handle2 && !this.handle2.attachable(this.handle1).canAccept) {
            if (warn) {
                Toast.warning("Destroying a connection because collection type has changed.");
            }
            this.destroy();
        }
    },
    redraw: function() {
        const handle1 = this.handle1;
        const handle2 = this.handle2;
        const startRibbon = handle1 && handle1.isMappedOver();
        const endRibbon = handle2 && handle2.isMappedOver();
        const canvas_container = $("#canvas-container");
        const canvasZoom = this.manager.canvasZoom;
        if (this.dragging) {
            this.canvas.style.zIndex = 1000;
        }
        this.canvas.setAttribute(
            "handle1-id",
            handle1 && handle1.element.getAttribute ? handle1.element.getAttribute("id") : ""
        );
        this.canvas.setAttribute(
            "handle2-id",
            handle2 && handle2.element.getAttribute ? handle2.element.getAttribute("id") : ""
        );
        const relativeLeft = e => ($(e).offset().left - canvas_container.offset().left) / canvasZoom;
        const relativeTop = e => ($(e).offset().top - canvas_container.offset().top) / canvasZoom;
        if (!handle1 || !handle2) {
            return;
        }
        // Find the position of each handle
        let start_x = relativeLeft(handle1.element) + 5;
        let start_y = relativeTop(handle1.element) + 5;
        let end_x = relativeLeft(handle2.element) + 5;
        let end_y = relativeTop(handle2.element) + 5;

        // Calculate canvas area
        const canvas_extra = 100;
        const canvas_min_x = Math.min(start_x, end_x);
        const canvas_max_x = Math.max(start_x, end_x);
        const canvas_min_y = Math.min(start_y, end_y);
        const canvas_max_y = Math.max(start_y, end_y);
        const canvas_left = canvas_min_x - canvas_extra;
        const canvas_top = canvas_min_y - canvas_extra;
        const canvas_width = canvas_max_x - canvas_min_x + 2 * canvas_extra;
        const canvas_height = canvas_max_y - canvas_min_y + 2 * canvas_extra;

        // Place the canvas
        this.canvas.style.left = `${canvas_left}px`;
        this.canvas.style.top = `${canvas_top}px`;
        this.svg.style("width", `${canvas_width}px`);
        this.svg.style("height", `${canvas_height}px`);

        // Adjust points to be relative to the canvas
        start_x -= canvas_left;
        start_y -= canvas_top;
        end_x -= canvas_left;
        end_y -= canvas_top;

        // Determine line shift
        const cp_factor = 10;
        const cp_shift = Math.min(Math.max(Math.abs(canvas_max_y - canvas_min_y) / 2, cp_factor), 300 / cp_factor);

        // Draw the line
        let start_offsets = null;
        let end_offsets = null;
        let num_offsets = 1;
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
        for (let i = 0; i < num_offsets; i++) {
            let inner_width = 5;
            let outer_width = 7;
            if (start_offsets.length > 1 || end_offsets.length > 1) {
                // We have a multi-run, using many lines, make them small.
                inner_width = 1;
                outer_width = 3;
            }
            this.draw_outlined_curve(
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
        offset_start = offset_start || 0;
        offset_end = offset_end || 0;
        const lineData = [
            { x: start_x, y: start_y + offset_start },
            { x: start_x + cp_shift,   y: start_y + offset_start},
            { x: end_x - cp_shift,  y: end_y + offset_end },
            { x: end_x,  y: end_y + offset_end } ];
        const lineFunction = d3.svg.line()
                                   .x(function(d) { return d.x; })
                                   .y(function(d) { return d.y; })
                                   .interpolate("basis");
        // The line SVG Path we draw
        this.svg.selectAll("*").remove();
        this.svg.append("path")
                .attr("d", lineFunction(lineData))
                .attr("stroke", this.inner_color)
                .attr("stroke-width", inner_width)
                .attr("fill", "none");
        this.svg.append("path")
                .attr("d", lineFunction(lineData))
                .attr("stroke", this.outer_color)
                .attr("stroke-width", outer_width)
                .attr("fill", "none");
    }
});
export default Connector;
