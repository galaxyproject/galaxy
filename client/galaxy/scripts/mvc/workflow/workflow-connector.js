import $ from "jquery";
import * as d3 from "d3";
import { Toast } from "ui/toast";

// Rendering parameters
const zIndex = 1000;
const cpFactor = 10;
const canvasExtra = 100;
const handleMarginX = 8;
const ribbonMargin = 4;
const ribbonInnerSingle = 4;
const ribbonOuterSingle = 6;
const ribbonInnerMultiple = 1;
const ribbonOuterMultiple = 3;

class Connector {
    constructor(manager = {}, handle1 = null, handle2 = null) {
        this.manager = manager;
        this.dragging = false;
        this.innerClass = "ribbon-inner";
        this.canvas = document.createElement("div");
        this.canvas.style.position = "absolute";
        const container = document.getElementById("canvas-container");
        container.appendChild(this.canvas);
        this.svg = d3.select(this.canvas).append("svg");
        this.svg.attr("class", "ribbon");
        if (handle1 && handle2) {
            this.connect(handle1, handle2);
        }
    }
    connect(t1, t2) {
        this.handle1 = t1;
        if (this.handle1) {
            this.handle1.connect(this);
        }
        this.handle2 = t2;
        if (this.handle2) {
            this.handle2.connect(this);
        }
    }
    destroy() {
        if (this.handle1) {
            this.handle1.disconnect(this);
        }
        if (this.handle2) {
            this.handle2.disconnect(this);
        }
        this.canvas.remove();
    }
    destroyIfInvalid(warn) {
        if (this.handle1 && this.handle2 && !this.handle2.attachable(this.handle1).canAccept) {
            if (warn) {
                Toast.warning("Destroying a connection because collection type has changed.");
            }
            this.destroy();
        }
    }
    dropStart(canAccept) {
        if (canAccept) {
            this.innerClass = "ribbon-inner-valid";
        } else {
            this.innerClass = "ribbon-inner-invalid";
        }
    }
    dropEnd() {
        this.innerClass = "ribbon-inner";
    }
    redraw() {
        // Identify handles
        const handle1 = this.handle1;
        const handle2 = this.handle2;
        const canvas_container = $("#canvas-container");
        const canvasZoom = this.manager.canvasZoom;
        if (this.dragging) {
            this.canvas.style.zIndex = zIndex;
        }
        this.canvas.setAttribute(
            "handle1-id",
            handle1 && handle1.element.getAttribute ? handle1.element.getAttribute("id") : ""
        );
        this.canvas.setAttribute(
            "handle2-id",
            handle2 && handle2.element.getAttribute ? handle2.element.getAttribute("id") : ""
        );
        const relativeLeft = (e) => ($(e).offset().left - canvas_container.offset().left) / canvasZoom;
        const relativeTop = (e) => ($(e).offset().top - canvas_container.offset().top) / canvasZoom;
        if (!handle1 || !handle2) {
            return;
        }

        // Find the position of each handle
        let start_x = relativeLeft(handle1.element) + handleMarginX;
        let start_y = relativeTop(handle1.element) + 0.5 * $(handle1.element).height();
        let end_x = relativeLeft(handle2.element) + handleMarginX;
        let end_y = relativeTop(handle2.element) + 0.5 * $(handle2.element).height();

        // Calculate canvas area
        const canvas_min_x = Math.min(start_x, end_x);
        const canvas_max_x = Math.max(start_x, end_x);
        const canvas_min_y = Math.min(start_y, end_y);
        const canvas_max_y = Math.max(start_y, end_y);
        const canvas_left = canvas_min_x - canvasExtra;
        const canvas_top = canvas_min_y - canvasExtra;
        const canvas_width = canvas_max_x - canvas_min_x + 2 * canvasExtra;
        const canvas_height = canvas_max_y - canvas_min_y + 2 * canvasExtra;

        // Place the canvas
        this.canvas.style.left = `${canvas_left}px`;
        this.canvas.style.top = `${canvas_top}px`;

        // Resize the svg
        this.svg.style("width", `${canvas_width}px`);
        this.svg.style("height", `${canvas_height}px`);

        // Adjust points to be relative to the canvas
        start_x -= canvas_left;
        start_y -= canvas_top;
        end_x -= canvas_left;
        end_y -= canvas_top;

        // Determine line shift
        const cp_shift = Math.min(Math.max(Math.abs(canvas_max_y - canvas_min_y) / 2, cpFactor), 3 * cpFactor);

        // Draw ribbons
        this.drawRibbon(handle1, handle2, cp_shift, start_x, start_y, end_x, end_y);
    }
    drawRibbon(handle1, handle2, cp_shift, start_x, start_y, end_x, end_y) {
        // Check ribbon type
        const startRibbon = handle1 && handle1.isMappedOver();
        const endRibbon = handle2 && handle2.isMappedOver();

        // Draw the line
        let start_offsets = [0];
        let end_offsets = [0];
        const offsets = [-2 * ribbonMargin, -ribbonMargin, 0, ribbonMargin, 2 * ribbonMargin];
        let num_offsets = 1;
        if (startRibbon) {
            start_offsets = offsets;
            num_offsets = offsets.length;
        }
        if (endRibbon) {
            end_offsets = offsets;
            num_offsets = offsets.length;
        }
        this.svg.selectAll("*").remove();
        for (let i = 0; i < num_offsets; i++) {
            let inner_width = ribbonInnerSingle;
            let outer_width = ribbonOuterSingle;
            if (start_offsets.length > 1 || end_offsets.length > 1) {
                inner_width = ribbonInnerMultiple;
                outer_width = ribbonOuterMultiple;
            }
            this.drawCurve(
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
    }
    drawCurve(start_x, start_y, end_x, end_y, cp_shift, inner_width, outer_width, offset_start, offset_end) {
        offset_start = offset_start || 0;
        offset_end = offset_end || 0;
        const lineData = [
            { x: start_x, y: start_y + offset_start },
            { x: start_x + cp_shift, y: start_y + offset_start },
            { x: end_x - cp_shift, y: end_y + offset_end },
            { x: end_x, y: end_y + offset_end },
        ];
        const lineFunction = d3.svg
            .line()
            .x(function (d) {
                return d.x;
            })
            .y(function (d) {
                return d.y;
            })
            .interpolate("basis");
        this.svg
            .append("path")
            .attr("class", "ribbon-outer")
            .attr("d", lineFunction(lineData))
            .attr("stroke-width", outer_width)
            .attr("fill", "none");
        this.svg
            .append("path")
            .attr("class", this.innerClass)
            .attr("d", lineFunction(lineData))
            .attr("stroke-width", inner_width)
            .attr("fill", "none");
    }
}
export default Connector;
