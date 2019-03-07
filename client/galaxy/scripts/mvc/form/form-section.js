/**
    This class creates a form section and populates it with input elements. It also handles repeat blocks and conditionals by recursively creating new sub sections.
*/
import $ from "jquery";
import _ from "underscore";
import Backbone from "backbone";
import Utils from "utils/utils";
import Portlet from "mvc/ui/ui-portlet";
import Repeat from "mvc/form/form-repeat";
import InputElement from "mvc/form/form-input";
import Parameters from "mvc/form/form-parameters";
var View = Backbone.View.extend({
    initialize: function(app, options) {
        this.app = app;
        this.inputs = options.inputs;
        this.parameters = new Parameters();
        this.setElement($("<div/>"));
        this.render();
    },

    /** Render section view */
    render: function() {
        var self = this;
        this.$el.empty();
        _.each(this.inputs, input => {
            self.add(input);
        });
    },

    /** Add a new input element */
    add: function(input) {
        var input_def = $.extend({}, input);
        input_def.id = Utils.uid();
        this.app.input_list[input_def.id] = input_def;
        switch (input_def.type) {
            case "conditional":
                this._addConditional(input_def);
                break;
            case "repeat":
                this._addRepeat(input_def);
                break;
            case "section":
                this._addSection(input_def);
                break;
            default:
                this._addRow(input_def);
        }
    },

    /** Add a conditional block */
    _addConditional: function(input_def) {
        var self = this;
        input_def.test_param.id = input_def.id;
        input_def.test_param.textable = false;
        this.app.model.get("sustain_conditionals") && (input_def.test_param.disabled = true);
        var field = this._addRow(input_def.test_param);
        // set onchange event for test parameter
        if (field.model) {
            // add conditional sub sections
            for (var i in input_def.cases) {
                var sub_section = new View(this.app, {
                    inputs: input_def.cases[i].inputs
                });
                this._append(sub_section.$el.addClass("ui-portlet-section pl-2"), `${input_def.id}-section-${i}`);
            }
            field.model.set("onchange", value => {
                var selectedCase = self.app.data.matchCase(input_def, value);
                for (var i in input_def.cases) {
                    var case_def = input_def.cases[i];
                    var section_row = self.$(`#${input_def.id}-section-${i}`);
                    var nonhidden = false;
                    for (var j in case_def.inputs) {
                        if (!case_def.inputs[j].hidden) {
                            nonhidden = true;
                            break;
                        }
                    }
                    if (i == selectedCase && nonhidden) {
                        section_row.fadeIn("fast");
                    } else {
                        section_row.hide();
                    }
                }
                self.app.trigger("change");
            });
            // trigger refresh on conditional input field after all input elements have been created
            field.trigger("change");
        }
    },

    /** Add a repeat block */
    _addRepeat: function(input_def) {
        var self = this;
        var block_index = 0;

        // create repeat block element
        var repeat = new Repeat.View({
            title: input_def.title || "Repeat",
            min: input_def.min,
            max: input_def.max,
            onnew: function() {
                create(input_def.inputs);
                self.app.trigger("change");
            }
        });

        // helper function to create new repeat blocks
        function create(inputs) {
            var sub_section_id = `${input_def.id}-section-${block_index++}`;
            var sub_section = new View(self.app, { inputs: inputs });
            repeat.add({
                id: sub_section_id,
                $el: sub_section.$el,
                ondel: function() {
                    repeat.del(sub_section_id);
                    self.app.trigger("change");
                }
            });
        }

        //
        // add parsed/minimum number of repeat blocks
        //
        var n_cache = _.size(input_def.cache);
        for (var i = 0; i < Math.max(Math.max(n_cache, input_def.min || 0), input_def.default || 0); i++) {
            create(i < n_cache ? input_def.cache[i] : input_def.inputs);
        }

        // hide options
        this.app.model.get("sustain_repeats") && repeat.hideOptions();

        // create input field wrapper
        var input_element = new InputElement(this.app, {
            label: input_def.title || input_def.name,
            help: input_def.help,
            field: repeat
        });
        this._append(input_element.$el, input_def.id);
    },

    /** Add a customized section */
    _addSection: function(input_def) {
        var portlet = new Portlet.View({
            title: input_def.title || input_def.name,
            cls: "ui-portlet-section",
            collapsible: true,
            collapsible_button: true,
            collapsed: !input_def.expanded
        });
        portlet.append(new View(this.app, { inputs: input_def.inputs }).$el);
        portlet.append(
            $("<div/>")
                .addClass("form-text text-muted")
                .html(input_def.help)
        );
        this.app.on("expand", input_id => {
            portlet.$(`#${input_id}`).length > 0 && portlet.expand();
        });
        this._append(portlet.$el, input_def.id);
    },

    /** Add a single input field element */
    _addRow: function(input_def) {
        var self = this;
        var id = input_def.id;
        input_def.onchange =
            input_def.onchange ||
            (() => {
                self.app.trigger("change", id);
            });
        var field = this.parameters.create(input_def);
        this.app.field_list[id] = field;
        var input_element = new InputElement(this.app, {
            name: input_def.name,
            label: input_def.hide_label ? "" : input_def.label || input_def.name,
            value: input_def.value,
            text_value: input_def.text_value,
            collapsible_value: input_def.collapsible_value,
            collapsible_preview: input_def.collapsible_preview,
            connectable: input_def.connectable,
            help: input_def.help,
            argument: input_def.argument,
            disabled: input_def.disabled,
            color: input_def.color,
            style: input_def.style,
            backdrop: input_def.backdrop,
            hidden: input_def.hidden,
            fixed: input_def.fixed,
            field: field
        });
        this.app.element_list[id] = input_element;
        this._append(input_element.$el, input_def.id);
        return field;
    },

    /** Append a new element to the form i.e. input element, repeat block, conditionals etc. */
    _append: function($el, id) {
        this.$el.append($el.addClass("section-row").attr("id", id));
    }
});

export default {
    View: View
};
