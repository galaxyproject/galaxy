define("mvc/form/form-repeat", ["exports", "utils/localization", "utils/utils", "mvc/ui/ui-portlet", "mvc/ui/ui-misc"], function(exports, _localization, _utils, _uiPortlet, _uiMisc) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });
    exports.View = undefined;

    var _localization2 = _interopRequireDefault(_localization);

    var _utils2 = _interopRequireDefault(_utils);

    var _uiPortlet2 = _interopRequireDefault(_uiPortlet);

    var _uiMisc2 = _interopRequireDefault(_uiMisc);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    var View = exports.View = Backbone.View.extend({
        initialize: function initialize(options) {
            this.list = {};
            this.options = _utils2.default.merge(options, {
                title: (0, _localization2.default)("Repeat"),
                empty_text: "Not available.",
                max: null,
                min: null
            });
            this.button_new = new _uiMisc2.default.ButtonIcon({
                icon: "fa-plus",
                title: "Insert " + this.options.title,
                tooltip: "Add new " + this.options.title + " block",
                cls: "ui-button-icon ui-clear-float form-repeat-add",
                onclick: function onclick() {
                    if (options.onnew) {
                        options.onnew();
                    }
                }
            });
            this.setElement($("<div/>").append(this.$list = $("<div/>")).append($("<div/>").append(this.button_new.$el)));
        },

        /** Number of repeat blocks */
        size: function size() {
            return _.size(this.list);
        },

        /** Add new repeat block */
        add: function add(options) {
            if (!options.id || this.list[options.id]) {
                Galaxy.emit.debug("form-repeat::add()", "Duplicate or invalid repeat block id.");
                return;
            }
            var button_delete = new _uiMisc2.default.ButtonIcon({
                icon: "fa-trash-o",
                tooltip: (0, _localization2.default)("Delete this repeat block"),
                cls: "ui-button-icon-plain form-repeat-delete",
                onclick: function onclick() {
                    if (options.ondel) {
                        options.ondel();
                    }
                }
            });
            var portlet = new _uiPortlet2.default.View({
                id: options.id,
                title: (0, _localization2.default)("placeholder"),
                cls: options.cls || "ui-portlet-repeat",
                operations: {
                    button_delete: button_delete
                }
            });
            portlet.append(options.$el);
            portlet.$el.addClass("section-row").hide();
            this.list[options.id] = portlet;
            this.$list.append(portlet.$el.fadeIn("fast"));
            if (this.options.max > 0 && this.size() >= this.options.max) {
                this.button_new.disable();
            }
            this._refresh();
        },

        /** Delete repeat block */
        del: function del(id) {
            if (!this.list[id]) {
                Galaxy.emit.debug("form-repeat::del()", "Invalid repeat block id.");
                return;
            }
            this.$list.find("#" + id).remove();
            delete this.list[id];
            this.button_new.enable();
            this._refresh();
        },

        /** Remove all */
        delAll: function delAll() {
            for (var id in this.list) {
                this.del(id);
            }
        },

        /** Hides add/del options */
        hideOptions: function hideOptions() {
            this.button_new.$el.hide();
            _.each(this.list, function(portlet) {
                portlet.hideOperation("button_delete");
            });
            if (_.isEmpty(this.list)) {
                this.$el.append($("<div/>").addClass("ui-form-info").html(this.options.empty_text));
            }
        },

        /** Refresh view */
        _refresh: function _refresh() {
            var index = 0;
            for (var id in this.list) {
                var portlet = this.list[id];
                portlet.title(++index + ": " + this.options.title);
                portlet[this.size() > this.options.min ? "showOperation" : "hideOperation"]("button_delete");
            }
        }
    });
    /** This class creates a ui component which enables the dynamic creation of portlets */
    exports.default = {
        View: View
    };
});
//# sourceMappingURL=../../../maps/mvc/form/form-repeat.js.map
