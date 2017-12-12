define("mvc/ui/ui-list", ["exports", "utils/utils", "mvc/ui/ui-portlet", "mvc/ui/ui-misc"], function(exports, _utils, _uiPortlet, _uiMisc) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _utils2 = _interopRequireDefault(_utils);

    var _uiPortlet2 = _interopRequireDefault(_uiPortlet);

    var _uiMisc2 = _interopRequireDefault(_uiMisc);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    // ui list element
    var View = Backbone.View.extend({
        // create portlet to keep track of selected list elements
        initialize: function initialize(options) {
            // link this
            var self = this;

            // initialize options
            this.options = options;
            this.name = options.name || "element";
            this.multiple = options.multiple || false;

            // create message handler
            this.message = new _uiMisc2.default.Message();

            // create portlet
            this.portlet = new _uiPortlet2.default.View({
                cls: "ui-portlet-section"
            });

            // create select field containing the options which can be inserted into the list
            this.select = new _uiMisc2.default.Select.View({
                optional: options.optional
            });

            // create insert new list element button
            this.button = new _uiMisc2.default.ButtonIcon({
                icon: "fa fa-sign-in",
                tooltip: "Insert new " + this.name,
                onclick: function onclick() {
                    self.add({
                        id: self.select.value(),
                        name: self.select.text()
                    });
                }
            });

            // build main element
            this.setElement(this._template(options));
            this.$(".ui-list-message").append(this.message.$el);
            this.$(".ui-list-portlet").append(this.portlet.$el);
            this.$(".ui-list-button").append(this.button.$el);
            this.$(".ui-list-select").append(this.select.$el);
        },

        /** Return/Set currently selected list elements */
        value: function value(val) {
            // set new value
            if (val !== undefined) {
                this.portlet.empty();
                if ($.isArray(val)) {
                    for (var i in val) {
                        var v = val[i];
                        var v_id = null;
                        var v_name = null;
                        if ($.type(v) != "string") {
                            v_id = v.id;
                            v_name = v.name;
                        } else {
                            v_id = v_name = v;
                        }
                        if (v_id != null) {
                            this.add({
                                id: v_id,
                                name: v_name
                            });
                        }
                    }
                }
                this._refresh();
            }
            // get current value
            var lst = [];
            this.$(".ui-list-id").each(function() {
                lst.push({
                    id: $(this).prop("id"),
                    name: $(this).find(".ui-list-name").html()
                });
            });
            if (lst.length == 0) {
                return null;
            }
            return lst;
        },

        /** Add row */
        add: function add(options) {
            var self = this;
            if (this.$("[id=\"" + options.id + "\"]").length === 0) {
                if (!_utils2.default.isEmpty(options.id)) {
                    var $el = $(this._templateRow({
                        id: options.id,
                        name: options.name
                    }));
                    $el.on("click", function() {
                        $el.remove();
                        self._refresh();
                    });
                    $el.on("mouseover", function() {
                        $el.addClass("portlet-highlight");
                    });
                    $el.on("mouseout", function() {
                        $el.removeClass("portlet-highlight");
                    });
                    this.portlet.append($el);
                    this._refresh();
                } else {
                    this.message.update({
                        message: "Please select a valid " + this.name + ".",
                        status: "danger"
                    });
                }
            } else {
                this.message.update({
                    message: "This " + this.name + " is already in the list."
                });
            }
        },

        /** Update available options */
        update: function update(options) {
            this.select.update(options);
        },

        /** Refresh view */
        _refresh: function _refresh() {
            if (this.$(".ui-list-id").length > 0) {
                !this.multiple && this.button.disable();
                this.$(".ui-list-portlet").show();
            } else {
                this.button.enable();
                this.$(".ui-list-portlet").hide();
            }
            this.options.onchange && this.options.onchange();
        },

        /** Main Template */
        _template: function _template(options) {
            return '<div class="ui-list">' + '<div class="ui-margin-top">' + '<span class="ui-list-button"/>' + '<span class="ui-list-select"/>' + "</div>" + '<div class="ui-list-message"/>' + '<div class="ui-list-portlet"/>' + "</div>";
        },

        /** Row Template */
        _templateRow: function _templateRow(options) {
            return "<div id=\"" + options.id + "\" class=\"ui-list-id\"><span class=\"ui-list-delete fa fa-trash\"/><span class=\"ui-list-name\">" + options.name + "</span></div>";
        }
    }); // dependencies
    exports.default = {
        View: View
    };
});
//# sourceMappingURL=../../../maps/mvc/ui/ui-list.js.map
