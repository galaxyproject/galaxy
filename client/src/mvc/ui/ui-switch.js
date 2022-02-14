import Backbone from "backbone";

/** Renders a switch input element used e.g. in the tool form */
export default Backbone.View.extend({
    initialize: function (options) {
        this.model =
            (options && options.model) ||
            new Backbone.Model({
                disabled: false,
                visible: true,
                onchange: () => {},
            }).set(options);
        this.setElement(this._template());
        this.$label = this.$(".label");
        this.$input = this.$(".custom-control-input");
        this.listenTo(this.model, "change", this.render, this);
        this.listenTo(this, "change", () => {
            this.model.get("onchange")(this.value());
        });
        this.render();
    },
    events: {
        input: "_onchange",
    },
    value: function (new_val) {
        new_val !== undefined && this.model.set("value", new_val);
        return this.model.get("value");
    },
    render: function () {
        if (this.model.get("value") == "true") {
            this.$label.text("Yes");
            this.$input.prop("checked", true);
        } else {
            this.$label.text("No");
            this.$input.prop("checked", false);
        }
        this.model.get("disabled") ? this.$input.attr("disabled", true) : this.$input.removeAttr("disabled");
        this.$el[this.model.get("visible") ? "show" : "hide"]();
        return this;
    },
    _onchange: function () {
        this.value(this.$input.prop("checked") ? "true" : "false");
        this.trigger("change");
    },
    _template: function () {
        const id = this.model.id;
        return `<div class="ui-switch">
                    <div class="custom-control" id="${id}">
                        <input type="checkbox" class="custom-control-input" id="switch-id-${id}" />
                        <label class="custom-control-label" for="switch-id-${id}"/>
                    </div>
                    <div class="label" />
                </div>`;
    },
});
