import $ from "jquery";

// Colors used to render nodes in the workflow overview
const NODE_COLOR = "#25537b";
const NODE_HIGHLIGHT_COLOR = "#400404";
const NODE_ERROR_COLOR = "#e31a1e";

const OVERLAY_HIGHLIGHT_INTERVAL = 20;
const OVERLAY_HIGHLIGHT_STEPS = 40;

// Zoom levels to use for zooming the workflow canvas
export const zoomLevels = [0.25, 0.33, 0.5, 0.67, 0.75, 0.8, 0.9, 1, 1.1, 1.25, 1.33, 1.5, 2, 2.5, 3, 4];

// Default zoome level
export const defaultZoomLevel = 7;
const inputElementTypes = ["input", "text", "textarea"];

// FIXME: merge scroll panel into CanvasManager, clean up hardcoded stuff.
class ScrollPanel {
    constructor(panel) {
        this.panel = panel;
    }
    test(e, onmove) {
        window.clearTimeout(this.timeout);
        var x = e.pageX;
        var y = e.pageY;
        // Panel size and position
        var panel = $(this.panel);
        var panel_pos = panel.position();
        var panel_w = panel.width();
        var panel_h = panel.height();
        // Viewport size and offset
        var viewport = panel.parent();
        var viewport_w = viewport.width();
        var viewport_h = viewport.height();
        var viewport_offset = viewport.offset();
        // Edges of viewport (in page coordinates)
        var min_x = viewport_offset.left;
        var min_y = viewport_offset.top;
        var max_x = min_x + viewport.width();
        var max_y = min_y + viewport.height();
        // Legal panel range
        var p_min_x = -(panel_w - viewport_w / 2);
        var p_min_y = -(panel_h - viewport_h / 2);
        var p_max_x = viewport_w / 2;
        var p_max_y = viewport_h / 2;
        // Did the panel move?
        var moved = false;
        // Constants
        var close_dist = 5;
        var nudge = 23;
        var t = 0;
        if (x - close_dist < min_x) {
            if (panel_pos.left < p_max_x) {
                t = Math.min(nudge, p_max_x - panel_pos.left);
                panel.css("left", panel_pos.left + t);
                moved = true;
            }
        } else if (x + close_dist > max_x) {
            if (panel_pos.left > p_min_x) {
                t = Math.min(nudge, panel_pos.left - p_min_x);
                panel.css("left", panel_pos.left - t);
                moved = true;
            }
        } else if (y - close_dist < min_y) {
            if (panel_pos.top < p_max_y) {
                t = Math.min(nudge, p_max_y - panel_pos.top);
                panel.css("top", panel_pos.top + t);
                moved = true;
            }
        } else if (y + close_dist > max_y) {
            if (panel_pos.top > p_min_y) {
                t = Math.min(nudge, panel_pos.top - p_min_x);
                panel.css("top", `${panel_pos.top - t}px`);
                moved = true;
            }
        }
        if (moved) {
            // Keep moving even if mouse doesn't move
            onmove();
            this.timeout = window.setTimeout(() => {
                this.test(e, onmove);
            }, 50);
        }
    }
    stop() {
        window.clearTimeout(this.timeout);
    }
}

class CanvasManager {
    constructor(app) {
        this.app = app;
        this.cv = $("#canvas-viewport");
        this.cc = this.cv.find("#canvas-container");
        this.overview = $("#overview-container");
        this.oc = this.overview.find("#overview-canvas");
        this.ov = this.overview.find("#overview-viewport");
        // Initialize zooming
        this.zoomLevel = defaultZoomLevel;
        this.canvasZoom = zoomLevels[defaultZoomLevel];
        // Make overview box draggable
        this.init_drag();
        // Initialize Copy & Paste events
        this.init_copy_paste();
        this.init_scroll_zoom();
        this.isWheeled = false;
    }
    setZoom(zoomLevel) {
        this.isWheeled = false;
        this.zoomLevel = Math.min(Math.max(0, zoomLevel), zoomLevels.length - 1);
        this.canvasZoom = zoomLevels[this.zoomLevel];
        // Set CSS transform to appropriate zoom level
        this.cv.css("transform-origin", "top left");
        this.cv.css("transform", "scale(" + this.canvasZoom + ")");
        // Modify canvas size to account for scale
        this.cv.css("width", `${100 / this.canvasZoom}%`);
        this.cv.css("height", `${100 / this.canvasZoom}%`);
        // Update canvas size
        this._fitCanvasToNodes();
        this.drawOverview();
        return this.zoomLevel;
    }
    init_scroll_zoom() {
        /*
            The scroll_zoom event binding allows for the functionality of zooming in
            using the mouse scroll wheel.
        */
        // Zooming within canvas background
        document.getElementById("workflow-canvas").addEventListener("wheel", (e) => {
            this.isWheeled = true;
            e.preventDefault();
            var zoomScale = this.canvasZoom;
            zoomScale += e.deltaY * -0.001;
            // // Get value within range of zoom/scale levels (0.25 - 4)
            zoomScale = Math.min(Math.max(0.25, zoomScale), 4);
            // Find index (zoomLevel) for the zoom value (canvasZoom)
            let zoomIndex = 0;
            while (zoomLevels[zoomIndex] < zoomScale) {
                zoomIndex++;
            }
            // Tried to use setZoom() function but it requires zoomLevel as input
            // i.e.: won't allow for smooth zooming (will only allow 15 levels
            // of zoom like in ZoomControl)
            // this.setZoom(i);
            this.zoomLevel = zoomIndex;
            this.canvasZoom = zoomScale;
            // Set CSS transform to appropriate zoom level
            this.cv.css("transform-origin", "top left");
            this.cv.css("transform", "scale(" + this.canvasZoom + ")");
            // Modify canvas size to account for scale
            this.cv.css("width", `${100 / this.canvasZoom}%`);
            this.cv.css("height", `${100 / this.canvasZoom}%`);
            // Update canvas size
            this._fitCanvasToNodes();
            this.drawOverview();
        });
    }
    move(x, y) {
        x = Math.min(x, this.cv.width() / 2);
        x = Math.max(x, -this.cc.width() + this.cv.width() / 2);
        y = Math.min(y, this.cv.height() / 2);
        y = Math.max(y, -this.cc.height() + this.cv.height() / 2);
        this.cc.css({
            left: x,
            top: y,
        });
        this.cv.css({
            "background-position-x": x,
            "background-position-y": y,
        });
        this.updateViewportOverlay();
    }
    init_drag() {
        var self = this;
        // Dragging within canvas background
        this.scrollPanel = new ScrollPanel(this.cc);
        var x_adjust;
        var y_adjust;
        this.cv
            .bind("click", function () {
                document.activeElement.blur();
            })
            .bind("dragstart", function () {
                var o = $(this).offset();
                var p = self.cc.position();
                y_adjust = p.top - o.top;
                x_adjust = p.left - o.left;
            })
            .bind("drag", (e, d) => {
                this.move((d.offsetX + x_adjust) / this.canvasZoom, (d.offsetY + y_adjust) / this.canvasZoom);
            })
            .bind("dragend", () => {
                self.drawOverview();
            });
        this.overview.click((e) => {
            if (self.overview.hasClass("blockaclick")) {
                self.overview.removeClass("blockaclick");
            } else {
                var in_w = self.cc.width();
                var in_h = self.cc.height();
                var o_w = self.oc.width();
                var o_h = self.oc.height();
                var new_x_offset = e.pageX - self.oc.offset().left - self.ov.width() / 2;
                var new_y_offset = e.pageY - self.oc.offset().top - self.ov.height() / 2;
                this.move(-((new_x_offset / o_w) * in_w), -((new_y_offset / o_h) * in_h));
                this.drawOverview();
            }
        });
        // Dragging for overview pane
        this.ov
            .bind("drag", (e, d) => {
                var in_w = self.cc.width();
                var in_h = self.cc.height();
                var o_w = self.oc.width();
                var o_h = self.oc.height();
                var new_x_offset = d.offsetX - self.overview.offset().left;
                var new_y_offset = d.offsetY - self.overview.offset().top;
                this.move(-((new_x_offset / o_w) * in_w), -((new_y_offset / o_h) * in_h));
            })
            .bind("dragend", () => {
                self.overview.addClass("blockaclick");
                self.drawOverview();
            });
        // Dragging for overview border (resize)
        $(".workflow-overview").bind("drag", function (e, d) {
            var op = $(this).offsetParent();
            var opo = op.offset();
            var new_size = Math.max(op.width() - (d.offsetX - opo.left), op.height() - (d.offsetY - opo.top));
            $(this).css({
                width: new_size,
                height: new_size,
            });
            self.drawOverview();
        });
        /*  Disable dragging for child element of the panel so that resizing can
                only be done by dragging the borders */
        $(".workflow-overview div").bind("drag", () => {});

        // Stores the size of the overview into local storage when it's resized
        $(".workflow-overview").bind("dragend", function (e, d) {
            const op = $(this).offsetParent();
            const opo = op.offset();
            const new_size = Math.max(op.width() - (d.offsetX - opo.left), op.height() - (d.offsetY - opo.top));
            localStorage.setItem("overview-size", `${new_size}px`);
        });

        // On load, set the size to the pref stored in local storage if it exists
        const overview_size = localStorage.getItem("overview-size");
        if (overview_size !== undefined) {
            $(".workflow-overview").css({
                width: overview_size,
                height: overview_size,
            });
        }
    }
    init_copy_paste() {
        /*
            The copy/paste event bindings check the active element
            and, if it's one of the text inputs, skip the workflow copy/paste
            logic so we don't interfere with standard copy/paste functionality.
            The copy binding also skips the node copy if text is currently highlighted.
        */
        document.addEventListener("copy", (e) => {
            if (
                document.activeElement &&
                !inputElementTypes.includes(document.activeElement.type) &&
                !document.getSelection().toString()
            ) {
                if (this.app.activeNode && this.app.activeNode.type !== "subworkflow") {
                    e.clipboardData.setData(
                        "application/json",
                        JSON.stringify({
                            nodeId: this.app.activeNode.id,
                        })
                    );
                    e.preventDefault();
                }
            }
        });
        document.addEventListener("paste", (e) => {
            if (document.activeElement && !inputElementTypes.includes(document.activeElement.type)) {
                let nodeId;
                try {
                    nodeId = JSON.parse(e.clipboardData.getData("application/json")).nodeId;
                } catch (error) {
                    console.debug(error);
                }
                if (nodeId && this.app.nodes[nodeId]) {
                    this.app.nodes[nodeId].onClone();
                }
                e.preventDefault();
            }
        });
    }
    updateViewportOverlay() {
        var cc = this.cc;
        var cv = this.cv;
        var oc = this.oc;
        var ov = this.ov;
        var in_w = cc.width();
        var in_h = cc.height();
        var o_w = oc.width();
        var o_h = oc.height();
        var cc_pos = cc.position();
        ov.css({
            left: -((cc_pos.left / in_w) * o_w),
            top: -((cc_pos.top / in_h) * o_h),
            // Subtract 2 to account for borders (maybe just change box sizing style instead?)
            width: (cv.width() / in_w) * o_w - 2,
            height: (cv.height() / in_h) * o_h - 2,
        });
    }
    drawOverview() {
        this._fitCanvasToNodes();
        var canvas_el = $("#overview-canvas");
        var size = canvas_el.parent().parent().width();
        var c = canvas_el.get(0).getContext("2d");
        var in_w = $("#canvas-container").width();
        var in_h = $("#canvas-container").height();
        var o_h;
        var shift_h;
        var o_w;
        var shift_w;
        // Fit canvas into overview area
        var cv_w = this.cv.width();
        var cv_h = this.cv.height();
        if (in_w < cv_w && in_h < cv_h) {
            // Canvas is smaller than viewport
            o_w = (in_w / cv_w) * size;
            shift_w = (size - o_w) / 2;
            o_h = (in_h / cv_h) * size;
            shift_h = (size - o_h) / 2;
        } else if (in_w < in_h) {
            // Taller than wide
            shift_h = 0;
            o_h = size;
            o_w = Math.ceil((o_h * in_w) / in_h);
            shift_w = (size - o_w) / 2;
        } else {
            // Wider than tall
            o_w = size;
            shift_w = 0;
            o_h = Math.ceil((o_w * in_h) / in_w);
            shift_h = (size - o_h) / 2;
        }
        canvas_el.parent().css({
            left: shift_w,
            top: shift_h,
            width: o_w,
            height: o_h,
        });
        canvas_el.attr("width", o_w);
        canvas_el.attr("height", o_h);

        const drawOverlayRectFor = (nodeElement, color) => {
            const position = nodeElement.position();
            const x = (position.left / in_w) * o_w;
            const y = (position.top / in_h) * o_h;
            const w = (nodeElement.width() / in_w) * o_w;
            const h = (nodeElement.height() / in_h) * o_h;
            c.fillStyle = color;
            c.fillRect(x, y, w, h);
        };

        this.highlightInOverlay = (node) => {
            const nodeElement = $(node.element);
            let i = 0;
            let colorTarget = NODE_COLOR;
            if (node.errors) {
                colorTarget = NODE_ERROR_COLOR;
            }
            const ramp = getRamp(NODE_HIGHLIGHT_COLOR, colorTarget, OVERLAY_HIGHLIGHT_STEPS);
            const interval = setInterval(function () {
                i++;
                drawOverlayRectFor(nodeElement, ramp[i]);
                if (i === OVERLAY_HIGHLIGHT_STEPS) {
                    clearInterval(interval);
                }
            }, OVERLAY_HIGHLIGHT_INTERVAL);
        };
        // Draw overview
        $.each(this.app.nodes, (id, node) => {
            const nodeElement = $(node.element);
            let color = NODE_COLOR;
            if (node.errors) {
                color = NODE_ERROR_COLOR;
            }
            drawOverlayRectFor(nodeElement, color);
        });
        this.updateViewportOverlay();
    }
    _fitCanvasToNodes() {
        // Math utils
        function round_up(x, n) {
            return Math.ceil(x / n) * n;
        }
        function fix_delta(x, n) {
            if (x < n || x > 3 * n) {
                const new_pos = (Math.ceil((x % n) / n) + 1) * n;
                return -(x - new_pos);
            }
            return 0;
        }
        // Span of all elements
        const canvasZoom = this.canvasZoom;
        const bounds = this._boundsForAllNodes();
        const position = this.cc.position();
        const parent = this.cc.parent();
        // Determine amount we need to expand on top/left
        let xmin_delta = fix_delta(bounds.xmin, 100);
        let ymin_delta = fix_delta(bounds.ymin, 100);
        // May need to expand farther to fill viewport
        xmin_delta = Math.max(xmin_delta, position.left);
        ymin_delta = Math.max(ymin_delta, position.top);
        const left = position.left - xmin_delta;
        const top = position.top - ymin_delta;
        // Same for width/height
        let width = round_up(bounds.xmax + 100, 100) + xmin_delta;
        let height = round_up(bounds.ymax + 100, 100) + ymin_delta;
        width = Math.max(width, -left + parent.width());
        height = Math.max(height, -top + parent.height());
        // Grow the canvas container
        this.cc.css({
            left: left / canvasZoom,
            top: top / canvasZoom,
            width: width,
            height: height,
        });
        // Move elements back if needed
        this.cc.children().each(function () {
            const p = $(this).position();
            $(this).css("left", (p.left + xmin_delta) / canvasZoom);
            $(this).css("top", (p.top + ymin_delta) / canvasZoom);
        });
    }
    _boundsForAllNodes() {
        let xmin = Infinity;
        let xmax = -Infinity;
        let ymin = Infinity;
        let ymax = -Infinity;
        let p;
        Object.values(this.app.nodes).forEach((node) => {
            const e = $(node.element);
            p = e.position();
            xmin = Math.min(xmin, p.left);
            xmax = Math.max(xmax, p.left + e.width());
            ymin = Math.min(ymin, p.top);
            ymax = Math.max(ymax, p.top + e.height());
        });
        return { xmin: xmin, xmax: xmax, ymin: ymin, ymax: ymax };
    }
    scrollToNode(node) {
        const e = $(node.element);
        const p = e.position();
        const cv = $("#canvas-viewport");

        const midX = p.left + e.width() / 2;
        const midY = p.top + e.height() / 2;
        const left = midX - cv.width() / 2;
        const top = midY - cv.height() / 2;
        this.move(-left, -top);
        this.highlightInOverlay(node);
    }
    scrollToNodes() {
        const cv = $("#canvas-viewport");
        const cc = $("#canvas-container");
        let top = 0;
        let left = 0;
        if (cc.width() != cv.width()) {
            left = (cv.width() - cc.width()) / 2;
        }
        if (cc.height() != cv.height()) {
            top = (cv.height() - cc.height()) / 2;
        }
        cc.css({ left: left, top: top });
    }
}

// https://stackoverflow.com/a/48129324
function rgbToHex(r, g, b) {
    return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
}

function hexToRgb(hex) {
    var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result
        ? {
              r: parseInt(result[1], 16),
              g: parseInt(result[2], 16),
              b: parseInt(result[3], 16),
          }
        : null;
}

// returns an array of startColor, colors between according to steps, and endColor
function getRamp(startColor, endColor, steps) {
    var ramp = [];

    ramp.push(startColor);

    var startColorRgb = hexToRgb(startColor);
    var endColorRgb = hexToRgb(endColor);

    var rInc = Math.round((endColorRgb.r - startColorRgb.r) / (steps + 1));
    var gInc = Math.round((endColorRgb.g - startColorRgb.g) / (steps + 1));
    var bInc = Math.round((endColorRgb.b - startColorRgb.b) / (steps + 1));

    for (var i = 0; i < steps; i++) {
        startColorRgb.r += rInc;
        startColorRgb.g += gInc;
        startColorRgb.b += bInc;

        ramp.push(rgbToHex(startColorRgb.r, startColorRgb.g, startColorRgb.b));
    }
    ramp.push(endColor);

    return ramp;
}

export default CanvasManager;
