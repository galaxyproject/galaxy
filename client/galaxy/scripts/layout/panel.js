import $ from "jquery";
import _ from "underscore";
import Backbone from "backbone";
import { getGalaxyInstance } from "app";

var MIN_PANEL_WIDTH = 160;
var MAX_PANEL_WIDTH = 800;

/** View for left/right panels used by Page view */
var SidePanel = Backbone.View.extend({
    initialize: function(options) {
        this.view = options.view;
        this.hidden = false;
        this.saved_size = null;
        this.hiddenByTool = false;
    },

    $center: function() {
        return this.$el.siblings("#center");
    },

    $toggleButton: function() {
        return this.$(".unified-panel-footer > .panel-collapse");
    },

    render: function() {
        var self = this;
        var panel = this.view;
        var components = this.view.model.attributes || {};
        this.$el.html(this._templatePanel(this.id));
        _.each(components.buttons, button => {
            self.$(".panel-header-buttons").append(button.$el);
        });
        this.$el.addClass(components.cls);
        this.$(".panel-header-text").html(_.escape(components.title));
        this.$(".unified-panel-body").append(panel.$el);
        panel.render();
    },

    /** panel dom template. id is 'right' or 'left' */
    _templatePanel: function() {
        return [this._templateHeader(), this._templateBody(), this._templateFooter()].join("");
    },

    /** panel dom template. id is 'right' or 'left' */
    _templateHeader: function(data) {
        return `<div class="unified-panel-header" unselectable="on">
                    <div class="unified-panel-header-inner">
                        <div class="panel-header-buttons"/>
                        <div class="panel-header-text"/>
                    </div>
                </div>
                <div class="unified-panel-controls"/>`;
    },

    /** panel dom template. id is 'right' or 'left' */
    _templateBody: function(data) {
        return '<div class="unified-panel-body"/>';
    },

    /** panel dom template. id is 'right' or 'left' */
    _templateFooter: function(data) {
        return [
            '<div class="unified-panel-footer">',
            '<div class="panel-collapse ',
            _.escape(this.id),
            '"/>',
            '<div class="drag"/>',
            "</div>"
        ].join("");
    },

    events: {
        "mousedown .unified-panel-footer > .drag": "_mousedownDragHandler",
        "click .unified-panel-footer > .panel-collapse": "toggle"
    },

    _mousedownDragHandler: function(ev) {
        var self = this;
        var draggingLeft = this.id === "left";
        // Save the mouse position and width of the element (panel) when the
        // drag interaction is first started
        var initialX = ev.pageX;
        var initialWidth = self.$el.width();

        function move(e) {
            var delta = e.pageX - initialX;
            var newWidth = draggingLeft ? initialWidth + delta : initialWidth - delta;
            // Limit range
            newWidth = Math.min(MAX_PANEL_WIDTH, Math.max(MIN_PANEL_WIDTH, newWidth));
            self.resize(newWidth);
        }

        // This is a page wide overlay that assists in capturing the move and
        // release of the mouse. If not provided, progress and end wouldn't fire
        // if the mouse moved out of the drag button area.
        $("#dd-helper")
            .show()
            .on("mousemove", move)
            .one("mouseup", function(e) {
                $(this)
                    .hide()
                    .off("mousemove", move);
            });
    },

    // TODO: the following three could be simplified I think
    // if panel is 'right' (this.id), move center right newSize number of pixels
    resize: function(newSize) {
        this.$el.css("width", newSize);
        this.$center().css(this.id, newSize);
        return this;
    },

    show: function() {
        if (!this.hidden) {
            return;
        }
        var self = this;
        var animation = {};
        var whichSide = this.id;
        animation[whichSide] = 0;
        self.$el
            .css(whichSide, -this.saved_size)
            .show()
            .animate(animation, "fast", () => {
                self.resize(self.saved_size);
            });
        self.hidden = false;
        self.$toggleButton().removeClass("hidden");
        return this;
    },

    hide: function() {
        if (this.hidden) {
            return;
        }
        var animation = {};
        var whichSide = this.id;
        this.saved_size = this.$el.width();
        animation[whichSide] = -this.saved_size;
        this.$el.animate(animation, "fast");
        this.$center().css(whichSide, 0);
        this.hidden = true;
        this.$toggleButton().addClass("hidden");
        return this;
    },

    toggle: function(ev) {
        this.hidden ? this.show() : this.hide();
        this.hiddenByTool = false;
        return this;
    },

    // ..............................................................
    //TODO: only used in message.mako?
    /**   */
    handle_minwidth_hint: function(hint) {
        var space = this.$center().width() - (this.hidden ? this.saved_size : 0);
        if (space < hint) {
            if (!this.hidden) {
                this.toggle();
                this.hiddenByTool = true;
            }
        } else {
            if (this.hiddenByTool) {
                this.toggle();
                this.hiddenByTool = false;
            }
        }
        return self;
    },

    /**   */
    force_panel: function(op) {
        if (op == "show") {
            return this.show();
        }
        if (op == "hide") {
            return this.hide();
        }
        return self;
    },

    toString: function() {
        return `SidePanel(${this.id})`;
    }
});

// ----------------------------------------------------------------------------
// TODO: side should be defined by page - not here
var LeftPanel = SidePanel.extend({
    id: "left"
});

var RightPanel = SidePanel.extend({
    id: "right"
});

/** Center panel with the ability to switch between iframe and view */
var CenterPanel = Backbone.View.extend({
    initialize: function(options) {
        this.setElement($(this.template()));
        this.$frame = this.$(".center-frame");
        this.$panel = this.$(".center-panel");
        this.$frame.on("load", this._iframeChangeHandler.bind(this));
    },

    /** Display iframe if its target url changes, hide center panel */
    _iframeChangeHandler: function(ev) {
        var iframe = ev.currentTarget;
        var location = iframe.contentWindow && iframe.contentWindow.location;
        var Galaxy = getGalaxyInstance();
        // Adding try/catch to manage a CORS error in toolshed. Accessing
        // location.host is a CORS no-no
        try {
            if (location && location.host) {
                $(iframe).show();
                this.$panel.empty().hide();
                Galaxy.trigger("center-frame:load", {
                    fullpath: location.pathname + location.search + location.hash,
                    pathname: location.pathname,
                    search: location.search,
                    hash: location.hash
                });
            }
        } catch (err) {
            console.warn("_iframeChangeHandler error", ev, location, Galaxy);
        }
    },

    /** Display a view in the center panel, hide iframe */
    display: function(view) {
        var contentWindow = this.$frame[0].contentWindow || {};
        var message = contentWindow.onbeforeunload && contentWindow.onbeforeunload();
        var Galaxy = getGalaxyInstance();
        if (!message || confirm(message)) {
            contentWindow.onbeforeunload = undefined;
            this.$frame.attr("src", "about:blank").hide();
            this.$panel
                .empty()
                .scrollTop(0)
                .append(view.$el || view)
                .show();
            Galaxy.trigger("center-panel:load", view);
        }
    },

    template: function() {
        return (
            '<div class="center-container">' +
            '<iframe id="galaxy_main" name="galaxy_main" frameborder="0" class="center-frame" />' +
            '<div class="center-panel" />' +
            "</div>"
        );
    },

    toString: function() {
        return "CenterPanel";
    }
});

export default {
    SidePanel: SidePanel,
    LeftPanel: LeftPanel,
    RightPanel: RightPanel,
    CenterPanel: CenterPanel
};
