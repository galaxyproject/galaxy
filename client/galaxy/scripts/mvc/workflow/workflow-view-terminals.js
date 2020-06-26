import $ from "jquery";
import Terminals from "mvc/workflow/workflow-terminals";
import Connector from "mvc/workflow/workflow-connector";
import ariaAlert from "utils/ariaAlert";

var NODEINDEX = 0;

class BaseInputTerminalView {
    constructor(app, options = {}) {
        this.app = app;
        this.el = document.createElement("div");
        this.el.className = "terminal input-terminal";
        const node = options.node;
        const input = options.input;
        const name = input.name;
        const nodeIndex = NODEINDEX++;
        this.id = `node-${nodeIndex}-input-${name}`;
        this.terminal = this.terminalForInput(input);
        this.terminal.node = node;
        this.terminal.name = name;
        this.terminal.label = input.label;
        node.input_terminals[name] = this.terminal;
        this.el.terminal = this.terminal;
        this.$el = $(this.el);
        this.$el.attr("input-name", name);
        this.$el.attr("id", this.id);
        this.$el.append($("<icon/>"));
        const self = this;
        this.$el.on("dropinit", (e, d) => self.onDropInit(e, d));
        this.$el.on("dropstart", (e, d) => self.onDropStart(e, d));
        this.$el.on("dropend", (e, d) => self.onDropEnd(e, d));
        this.$el.on("drop", (e, d) => self.onDrop(e, d));
        this.$el.on("hover", () => self.onHover());
        this.terminal.on("change", this.render.bind(this));
    }
    render() {
        if (this.terminal.mapOver && this.terminal.mapOver.isCollection) {
            this.$el.addClass("multiple");
        } else {
            this.$el.removeClass("multiple");
        }
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
            const c = new Connector(this.app.canvas_manager, d.drag.terminal, terminal);
            c.redraw();
        }
    }
    onHover() {
        const terminal = this.terminal;
        // If connected, create a popup to allow disconnection
        if (terminal.connectors.length > 0) {
            const t = $("<div/>")
                .addClass("delete-terminal")
                .click(() => {
                    $.each(terminal.connectors, (_, x) => {
                        if (x) {
                            x.destroy();
                        }
                    });
                    t.remove();
                })
                .on("mouseleave", () => {
                    t.remove();
                });
            $(this.el).parent().append(t);
        }
    }
}

export class InputTerminalView extends BaseInputTerminalView {
    constructor(app, options = {}) {
        super(app, options);
    }
    terminalForInput(input) {
        return new Terminals.InputTerminal({
            app: this.app,
            element: this.el,
            input: input,
        });
    }
}

export class InputParameterTerminalView extends BaseInputTerminalView {
    constructor(app, options = {}) {
        super(app, options);
    }
    terminalForInput(input) {
        return new Terminals.InputParameterTerminal({
            app: this.app,
            element: this.el,
            input: input,
        });
    }
}

export class InputCollectionTerminalView extends BaseInputTerminalView {
    constructor(app, options = {}) {
        super(app, options);
    }
    terminalForInput(input = {}) {
        return new Terminals.InputCollectionTerminal({
            app: this.app,
            element: this.el,
            input: input,
        });
    }
}

export class BaseOutputTerminalView {
    constructor(app, options) {
        this.app = app;
        this.el = document.createElement("div");
        this.el.className = "terminal output-terminal";
        const node = options.node;
        const output = options.output;
        const name = output.name;
        const nodeIndex = NODEINDEX++;
        this.id = `node-${nodeIndex}-output-${name}`;
        this.terminal = this.terminalForOutput(output);
        this.terminal.node = node;
        this.terminal.name = name;
        this.terminal.label = output.label;
        node.output_terminals[name] = this.terminal;
        this.el.terminal = this.terminal;
        this.$el = $(this.el);
        this.$el.attr("output-name", name);
        this.$el.attr("id", this.id);
        this.$el.append($("<icon/>"));
        this.$el.attr(
            "aria-label",
            `connect output ${name} from ${node.name} to input. Press space to see a list of available inputs`
        );
        this.$el.attr("tabindex", "0");
        this.$el.attr("aria-grabbed", "false");
        const self = this;
        this.$el.on("drag", (d, e) => self.onDrag(d, e));
        this.$el.on("dragstart", (d, e) => self.onDragStart(d, e));
        this.$el.on("dragend", (d, e) => self.onDragEnd(d, e));
        this.$el.on("keydown", (e) => self.screenReaderSelectOutputNode(e));
        this.terminal.on("change", this.render.bind(this));
    }
    render() {
        if (this.terminal.mapOver && this.terminal.mapOver.isCollection) {
            this.$el.addClass("multiple");
        } else {
            this.$el.removeClass("multiple");
        }
    }
    screenReaderSelectOutputNode(e) {
        const inputChoiceKeyDown = (e) => {
            e.stopPropagation();
            const currentItem = e.currentTarget;
            const previousItem = currentItem.previousSibling;
            const nextItem = currentItem.nextSibling;
            const inputTerminal = currentItem.input.context.terminal;
            const switchActiveItem = (currentActive, newActive) => {
                newActive.classList.add("active");
                newActive.focus();
                currentActive.classList.remove("active");
            };
            const removeMenu = () => {
                $(currentItem.parentNode).remove();
                this.$el.removeAttr("aria-owns");
                this.$el.attr("aria-grabbed", "false");
                this.$el.focus();
            };
            switch (e.keyCode) {
                case 40: // Down arrow
                    if (nextItem) {
                        switchActiveItem(currentItem, nextItem);
                    } else {
                        switchActiveItem(currentItem, currentItem.parentNode.firstChild);
                    }
                    break;
                case 38: // Up arrow
                    if (previousItem) {
                        switchActiveItem(currentItem, previousItem);
                    } else {
                        switchActiveItem(currentItem, currentItem.parentNode.lastChild);
                    }
                    break;
                case 32: // Space
                    removeMenu();
                    new Connector(this.app.canvas_manager, this.terminal, inputTerminal).redraw();
                    ariaAlert("Node connected");
                    if (inputTerminal.connectors.length > 0) {
                        const t = $("<div/>")
                            .addClass("delete-terminal")
                            .attr("tabindex", "0")
                            .attr("aria-label", "delete terminal")
                            .on("keydown click", (e) => {
                                if (e.keyCode === 32 || e.type === "click") {
                                    //Space or Click
                                    $.each(inputTerminal.connectors, (_, x) => {
                                        if (x) {
                                            x.destroy();
                                            ariaAlert("Connection destroyed");
                                        }
                                    });
                                    t.remove();
                                }
                            });
                        $(currentItem.input).parent().append(t);
                    }
                    break;
            }
        };
        const buildInputChoicesMenu = () => {
            const inputChoicesMenu = document.createElement("ul");
            $(inputChoicesMenu).focusout((e) => {
                /* focus is still inside child element of menu so don't hide */
                if (inputChoicesMenu.contains(e.relatedTarget)) {
                    return;
                }
                $(inputChoicesMenu).hide();
            });
            inputChoicesMenu.id = "input-choices-menu";
            inputChoicesMenu.className = "list-group";
            inputChoicesMenu.setAttribute("role", "menu");
            this.$el.attr("aria-grabbed", "true");
            this.$el.attr("aria-owns", "input-choices-menu");
            $(".input-terminal").each((i, el) => {
                const input = $(el);
                const inputTerminal = input.context.terminal;
                const connectionAcceptable = inputTerminal.canAccept(this.terminal);
                if (connectionAcceptable.canAccept) {
                    const inputChoiceItem = document.createElement("li");
                    inputChoiceItem.textContent = `${inputTerminal.name} in ${inputTerminal.node.name} node`;
                    inputChoiceItem.tabIndex = -1;
                    inputChoiceItem.input = input;
                    inputChoiceItem.onkeydown = inputChoiceKeyDown;
                    inputChoiceItem.className = "list-group-item";
                    inputChoiceItem.setAttribute("role", "menuitem");
                    inputChoicesMenu.appendChild(inputChoiceItem);
                }
            });
            if (inputChoicesMenu.firstChild) {
                this.$el.append(inputChoicesMenu);
                inputChoicesMenu.firstChild.classList.add("active");
                inputChoicesMenu.firstChild.focus();
            } else {
                ariaAlert("There are no available inputs for this selected output");
            }
        };
        if (e.keyCode === 32) {
            //Space
            ariaAlert("Node selected");
            buildInputChoicesMenu();
        }
    }
    onDrag(e, d = {}) {
        var onmove = () => {
            var canvasZoom = this.app.canvas_manager.canvasZoom;
            var po = $(d.proxy).offsetParent().offset();

            var x = d.offsetX - po.left;
            var y = d.offsetY - po.top;
            $(d.proxy).css({ left: x / canvasZoom, top: y / canvasZoom });
            d.proxy.terminal.redraw();
            this.app.canvas_manager.update_viewport_overlay();
        };
        onmove();
        $("#canvas-container").get(0).scroll_panel.test(e, onmove);
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
        h.terminal = new Terminals.OutputTerminal({ element: h });
        const c = new Connector(this.app.canvas_manager);
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
        $("#canvas-container").get(0).scroll_panel.stop();
    }
}

export class OutputTerminalView extends BaseOutputTerminalView {
    constructor(app, options = {}) {
        super(app, options);
    }
    terminalForOutput(output) {
        var type = output.extensions;
        return new Terminals.OutputTerminal({
            element: this.el,
            datatypes: type,
            force_datatype: output.force_datatype,
            optional: output.optional,
        });
    }
}

export class OutputCollectionTerminalView extends BaseOutputTerminalView {
    constructor(app, options = {}) {
        super(app, options);
    }
    terminalForOutput(output) {
        var collection_type = output.collection_type;
        var collection_type_source = output.collection_type_source;
        return new Terminals.OutputCollectionTerminal({
            element: this.el,
            collection_type: collection_type,
            collection_type_source: collection_type_source,
            datatypes: output.extensions,
            force_datatype: output.force_datatype,
            optional: output.optional,
        });
    }
}

export class OutputParameterTerminalView extends BaseOutputTerminalView {
    constructor(app, options = {}) {
        super(app, options);
    }
    terminalForOutput(output) {
        return new Terminals.OutputParameterTerminal({
            element: this.el,
            type: output.type,
            optional: output.optional,
        });
    }
}

export default {
    InputTerminalView: InputTerminalView,
    InputParameterTerminalView: InputParameterTerminalView,
    InputCollectionTerminalView: InputCollectionTerminalView,
    OutputTerminalView: OutputTerminalView,
    OutputParameterTerminalView: OutputParameterTerminalView,
    OutputCollectionTerminalView: OutputCollectionTerminalView,
};
