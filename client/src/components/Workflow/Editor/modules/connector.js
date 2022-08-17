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

function offset(element) {
    const rect = element.getBoundingClientRect();
    return {
        top: rect.top + window.scrollY,
        left: rect.left + window.scrollX,
    };
}

class Connector {
    constructor(canvasManager = {}, outputHandle = null, inputHandle = null) {
        this.manager = canvasManager;
        this.dragging = false;
        this.innerClass = "ribbon-inner";
        this.canvas = document.createElement("div");
        this.canvas.style.position = "absolute";
        const container = document.getElementById("canvas-container");
        container.appendChild(this.canvas);
        this.svg = d3.select(this.canvas).append("svg");
        this.svg.attr("class", "ribbon");
        if (outputHandle && inputHandle) {
            this.connect(outputHandle, inputHandle);
        }
    }
    connect(t1, t2) {
        this.outputHandle = t1;
        this.outputHandle?.connect(this);
        this.inputHandle = t2;
        this.inputHandle?.connect(this);
    }
    destroy() {
        this.outputHandle?.disconnect(this);
        this.inputHandle?.disconnect(this);
        this.canvas.remove();
    }
    destroyIfInvalid(warn) {
        if (this.outputHandle && this.inputHandle && !this.inputHandle.attachable(this.outputHandle).canAccept) {
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
        const outputHandle = this.outputHandle;
        const inputHandle = this.inputHandle;
        if (!outputHandle || !inputHandle) {
            return;
        }
        if (this.dragging) {
            this.canvas.style.zIndex = zIndex;
        }
        if (!outputHandle || !inputHandle) {
            return;
        }
        // Set handle ids, used in test cases
        this.canvas.setAttribute("output-handle-id", outputHandle.element.getAttribute("id"));
        this.canvas.setAttribute("input-handle-id", inputHandle.element.getAttribute("id"));

        // Find the position of each handle
        const canvasContainer = document.getElementById("canvas-container");
        const canvasZoom = this.manager.canvasZoom;

        const relativeLeft = (e) => (offset(e).left - offset(canvasContainer).left) / canvasZoom + handleMarginX;
        const relativeTop = (e) =>
            (offset(e).top - offset(canvasContainer).top) / canvasZoom + 0.5 * inputHandle.element.offsetHeight;

        let start_x = relativeLeft(outputHandle.element);
        let start_y = relativeTop(outputHandle.element);
        let end_x = relativeLeft(inputHandle.element);
        let end_y = relativeTop(inputHandle.element);

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
        this.drawRibbon(outputHandle, inputHandle, cp_shift, start_x, start_y, end_x, end_y);
    }
    drawRibbon(outputHandle, inputHandle, cp_shift, start_x, start_y, end_x, end_y) {
        // Check ribbon type
        const startRibbon = outputHandle && outputHandle.isMappedOver();
        const endRibbon = inputHandle && inputHandle.isMappedOver();

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
