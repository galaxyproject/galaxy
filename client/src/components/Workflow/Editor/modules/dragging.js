import $ from "jquery";
import Terminals from "./terminals";
import Connector from "./connector";
import { ariaSelectOutputNode } from "./aria";

export function attachDragging(el, callbacks) {
    const $el = $(el);
    Object.entries(callbacks).forEach(([k, v]) => {
        $el.bind(k, v);
    });
}

export class InputDragging {
    constructor(app, options = {}) {
        this.app = app;
        this.el = options.el;
        this.terminal = options.terminal;
        this.el.terminal = this.terminal;
        this.$el = $(this.el);
        this.$el.on("dropinit", (e, d) => this.onDropInit(e, d));
        this.$el.on("dropstart", (e, d) => this.onDropStart(e, d));
        this.$el.on("dropend", (e, d) => this.onDropEnd(e, d));
        this.$el.on("drop", (e, d) => this.onDrop(e, d));
    }
    onDropInit(e, d = {}) {
        var terminal = this.terminal;
        // Accept a dragable if it is an output terminal and has a
        // compatible type
        var connectionAcceptable = $(d.drag).hasClass("output-terminal") && terminal.canAccept(d.drag.terminal);
        if (connectionAcceptable.canAccept) {
            this.$el.addClass("can-accept");
            this.$el.removeClass("cannot-accept");
            this.reason = null;
        } else {
            this.$el.addClass("cannot-accept");
            this.$el.removeClass("can-accept");
            this.reason = connectionAcceptable.reason;
        }
        return true;
    }
    onDropStart(e, d = {}) {
        if (d.proxy.terminal) {
            if (this.$el.hasClass("can-accept")) {
                d.proxy.terminal.connectors[0].dropStart(true);
                d.proxy.dropTooltip = "";
            } else {
                d.proxy.terminal.connectors[0].dropStart(false);
                if (this.reason) {
                    d.proxy.dropTooltip = this.reason;
                    $(d.proxy).tooltip("show");
                } else {
                    d.proxy.dropTooltip = "";
                }
            }
        }
    }
    onDropEnd(e, d = {}) {
        d.proxy.dropTooltip = "";
        if (d.proxy.terminal) {
            d.proxy.terminal.connectors[0].dropEnd();
        }
    }
    onDrop(e, d = {}) {
        d.proxy.dropTooltip = "";
        if (this.$el.hasClass("can-accept")) {
            const terminal = this.terminal;
            const c = new Connector(this.app.canvasManager, d.drag.terminal, terminal);
            c.redraw();
        }
    }
}

export class OutputDragging {
    constructor(app, options) {
        this.app = app;
        this.el = options.el;
        this.terminal = options.terminal;
        this.el.terminal = this.terminal;
        this.$el = $(this.el);
        this.$el.attr(
            "aria-label",
            `connect output ${this.terminal.name} to input. Press space to see a list of available inputs`
        );
        this.$el.attr("tabindex", "0");
        this.$el.attr("aria-grabbed", "false");
        this.$el.on("drag", (e, d) => this.onDrag(e, d));
        this.$el.on("dragstart", (e, d) => this.onDragStart(e, d));
        this.$el.on("dragend", (e, d) => this.onDragEnd(e, d));
        this.$el.on("keydown", (e) =>
            ariaSelectOutputNode({
                e: e,
                manager: app,
                outputTerminal: options.terminal,
                outputEl: this.el,
            })
        );
    }
    onDrag(e, d = {}) {
        var onmove = () => {
            var canvasZoom = this.app.canvasManager.canvasZoom;
            var po = $(d.proxy).offsetParent().offset();
            var x = d.offsetX - po.left;
            var y = d.offsetY - po.top;
            $(d.proxy).css({ left: x / canvasZoom, top: y / canvasZoom });
            d.proxy.terminal.redraw();
            this.app.canvasManager.updateViewportOverlay();
        };
        onmove();
        this.app.canvasManager.scrollPanel.test(e, onmove);
    }
    onDragStart(e, d = {}) {
        $(d.available).addClass("input-terminal-active");
        // Drag proxy div
        var h = $("<div class='drag-terminal'/>").appendTo("#canvas-container").get(0);
        h.dropTooltip = "";
        // Terminal and connection to display noodle while dragging
        $(h).tooltip({
            title: function () {
                return h.dropTooltip || "";
            },
        });
        h.terminal = new Terminals.Terminal({ element: h, node: {} });
        const c = new Connector(this.app.canvasManager);
        c.dragging = true;
        c.connect(this.terminal, h.terminal);
        return h;
    }
    onDragEnd(e, d = {}) {
        var connector = d.proxy.terminal.connectors[0];
        if (connector) {
            connector.destroy();
        }
        $(d.proxy).tooltip("dispose");
        $(d.proxy).remove();
        $(d.available).removeClass("input-terminal-active");
        this.app.canvasManager.scrollPanel.stop();
    }
}
