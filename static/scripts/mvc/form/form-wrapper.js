define("mvc/form/form-wrapper", ["exports", "mvc/form/form-view", "mvc/ui/ui-misc"], function(exports, _formView, _uiMisc) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _formView2 = _interopRequireDefault(_formView);

    var _uiMisc2 = _interopRequireDefault(_uiMisc);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    /** Generic form view */
    var View = Backbone.View.extend({
        initialize: function initialize(options) {
            this.model = new Backbone.Model(options);
            this.url = this.model.get("url");
            this.redirect = this.model.get("redirect");
            this.setElement("<div/>");
            this.render();
        },

        render: function render() {
            var self = this;
            $.ajax({
                url: Galaxy.root + this.url,
                type: "GET"
            }).done(function(response) {
                var options = $.extend({}, self.model.attributes, response);
                var form = new _formView2.default({
                    title: options.title,
                    message: options.message,
                    status: options.status || "warning",
                    icon: options.icon,
                    initial_errors: true,
                    errors: options.errors,
                    inputs: options.inputs,
                    buttons: {
                        submit: new _uiMisc2.default.Button({
                            tooltip: options.submit_tooltip,
                            title: options.submit_title || "Save",
                            icon: options.submit_icon || "fa-save",
                            cls: "btn btn-primary ui-clear-float",
                            onclick: function onclick() {
                                self._submit(form);
                            }
                        })
                    }
                });
                self.$el.empty().append(form.$el);
            }).fail(function(response) {
                self.$el.empty().append(new _uiMisc2.default.Message({
                    message: "Failed to load resource " + self.url + ".",
                    status: "danger",
                    persistent: true
                }).$el);
            });
        },

        _submit: function _submit(form) {
            var self = this;
            $.ajax({
                url: Galaxy.root + self.url,
                data: JSON.stringify(form.data.create()),
                type: "PUT",
                contentType: "application/json"
            }).done(function(response) {
                var params = {};
                if (response.id) {
                    params.id = response.id;
                } else {
                    params = {
                        message: response.message,
                        status: "success",
                        persistent: false
                    };
                }
                if (self.redirect) {
                    window.location = Galaxy.root + self.redirect + "?" + $.param(params);
                } else {
                    form.data.matchModel(response, function(input, input_id) {
                        form.field_list[input_id].value(input.value);
                    });
                    self._showMessage(form, success_message);
                }
            }).fail(function(response) {
                self._showMessage(form, {
                    message: response.responseJSON.err_msg,
                    status: "danger",
                    persistent: false
                });
            });
        },

        _showMessage: function _showMessage(form, options) {
            var $panel = form.$el.parents().filter(function() {
                return ["auto", "scroll"].indexOf($(this).css("overflow")) != -1;
            }).first();
            $panel.animate({
                scrollTop: 0
            }, 500);
            form.message.update(options);
        }
    });

    exports.default = {
        View: View
    };
});
//# sourceMappingURL=../../../maps/mvc/form/form-wrapper.js.map
