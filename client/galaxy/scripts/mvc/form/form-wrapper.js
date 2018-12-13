/** Generic form view */
import $ from "jquery";
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import Form from "mvc/form/form-view";
import Ui from "mvc/ui/ui-misc";

var View = Backbone.View.extend({
    initialize: function(options) {
        this.model = new Backbone.Model(options);
        this.url = this.model.get("url");
        this.redirect = this.model.get("redirect");
        if (options && options.active_tab) {
            this.active_tab = options.active_tab;
        }
        this.setElement("<div/>");
        this.render();
    },

    render: function() {
        var self = this;
        $.ajax({
            url: getAppRoot() + this.url,
            type: "GET"
        })
            .done(response => {
                var options = $.extend({}, self.model.attributes, response);
                var form = new Form({
                    title: options.title,
                    title_id: options.title_id,
                    message: options.message,
                    status: options.status || "warning",
                    icon: options.icon,
                    initial_errors: true,
                    errors: options.errors,
                    inputs: options.inputs,
                    buttons: {
                        submit: new Ui.Button({
                            tooltip: options.submit_tooltip,
                            title: options.submit_title || "Save",
                            icon: options.submit_icon || "fa-save",
                            cls: "btn btn-primary",
                            onclick: function() {
                                self._submit(form);
                            }
                        })
                    }
                });
                self.$el.empty().append(form.$el);
            })
            .fail(response => {
                self.$el.empty().append(
                    new Ui.Message({
                        message: `Failed to load resource ${self.url}.`,
                        status: "danger",
                        persistent: true
                    }).$el
                );
            });
    },

    _submit: function(form) {
        var self = this;
        $.ajax({
            url: getAppRoot() + self.url,
            data: JSON.stringify(form.data.create()),
            type: "PUT",
            contentType: "application/json"
        })
            .done(response => {
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
                    window.location = `${getAppRoot() + self.redirect}?${$.param(params)}`;
                } else {
                    form.data.matchModel(response, (input, input_id) => {
                        form.field_list[input_id].value(input.value);
                    });
                    self._showMessage(form, response.message);
                }
            })
            .fail(response => {
                self._showMessage(form, {
                    message: response.responseJSON.err_msg,
                    status: "danger",
                    persistent: false
                });
            });
    },

    _showMessage: function(form, options) {
        var $panel = form.$el
            .parents()
            .filter(function() {
                return ["auto", "scroll"].indexOf($(this).css("overflow")) != -1;
            })
            .first();
        $panel.animate({ scrollTop: 0 }, 500);
        form.message.update(options);
    }
});

export default {
    View: View
};
