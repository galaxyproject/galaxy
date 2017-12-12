define("mvc/form/form-section", ["exports", "utils/utils", "mvc/ui/ui-misc", "mvc/ui/ui-portlet", "mvc/form/form-repeat", "mvc/form/form-input", "mvc/form/form-parameters"], function(exports, _utils, _uiMisc, _uiPortlet, _formRepeat, _formInput, _formParameters) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _utils2 = _interopRequireDefault(_utils);

    var _uiMisc2 = _interopRequireDefault(_uiMisc);

    var _uiPortlet2 = _interopRequireDefault(_uiPortlet);

    var _formRepeat2 = _interopRequireDefault(_formRepeat);

    var _formInput2 = _interopRequireDefault(_formInput);

    var _formParameters2 = _interopRequireDefault(_formParameters);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    /**
        This class creates a form section and populates it with input elements. It also handles repeat blocks and conditionals by recursively creating new sub sections.
    */
    var View = Backbone.View.extend({
        initialize: function initialize(app, options) {
            this.app = app;
            this.inputs = options.inputs;
            this.parameters = new _formParameters2.default();
            this.setElement($("<div/>"));
            this.render();
        },

        /** Render section view */
        render: function render() {
            var self = this;
            this.$el.empty();
            _.each(this.inputs, function(input) {
                self.add(input);
            });
        },

        /** Add a new input element */
        add: function add(input) {
            var input_def = jQuery.extend(true, {}, input);
            input_def.id = input.id = _utils2.default.uid();
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
        _addConditional: function _addConditional(input_def) {
            var self = this;
            input_def.test_param.id = input_def.id;
            this.app.model.get("sustain_conditionals") && (input_def.test_param.disabled = true);
            var field = this._addRow(input_def.test_param);

            // set onchange event for test parameter
            field.model && field.model.set("onchange", function(value) {
                var selectedCase = self.app.data.matchCase(input_def, value);
                for (var i in input_def.cases) {
                    var case_def = input_def.cases[i];
                    var section_row = self.$("#" + input_def.id + "-section-" + i);
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

            // add conditional sub sections
            for (var i in input_def.cases) {
                var sub_section = new View(this.app, {
                    inputs: input_def.cases[i].inputs
                });
                this._append(sub_section.$el.addClass("ui-form-section"), input_def.id + "-section-" + i);
            }

            // trigger refresh on conditional input field after all input elements have been created
            field.trigger("change");
        },

        /** Add a repeat block */
        _addRepeat: function _addRepeat(input_def) {
            var self = this;
            var block_index = 0;

            // create repeat block element
            var repeat = new _formRepeat2.default.View({
                title: input_def.title || "Repeat",
                min: input_def.min,
                max: input_def.max,
                onnew: function onnew() {
                    create(input_def.inputs);
                    self.app.trigger("change");
                }
            });

            // helper function to create new repeat blocks
            function create(inputs) {
                var sub_section_id = input_def.id + "-section-" + block_index++;
                var sub_section = new View(self.app, {
                    inputs: inputs
                });
                repeat.add({
                    id: sub_section_id,
                    $el: sub_section.$el,
                    ondel: function ondel() {
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
            var input_element = new _formInput2.default(this.app, {
                label: input_def.title || input_def.name,
                help: input_def.help,
                field: repeat
            });
            this._append(input_element.$el, input_def.id);
        },

        /** Add a customized section */
        _addSection: function _addSection(input_def) {
            var portlet = new _uiPortlet2.default.View({
                title: input_def.title || input_def.name,
                cls: "ui-portlet-section",
                collapsible: true,
                collapsible_button: true,
                collapsed: !input_def.expanded
            });
            portlet.append(new View(this.app, {
                inputs: input_def.inputs
            }).$el);
            portlet.append($("<div/>").addClass("ui-form-info").html(input_def.help));
            this.app.on("expand", function(input_id) {
                portlet.$("#" + input_id).length > 0 && portlet.expand();
            });
            this._append(portlet.$el, input_def.id);
        },

        /** Add a single input field element */
        _addRow: function _addRow(input_def) {
            var self = this;
            var id = input_def.id;
            input_def.onchange = input_def.onchange || function() {
                self.app.trigger("change", id);
            };
            var field = this.parameters.create(input_def);
            this.app.field_list[id] = field;
            var input_element = new _formInput2.default(this.app, {
                name: input_def.name,
                label: input_def.hide_label ? "" : input_def.label || input_def.name,
                value: input_def.value,
                text_value: input_def.text_value,
                collapsible_value: input_def.collapsible_value,
                collapsible_preview: input_def.collapsible_preview,
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
        _append: function _append($el, id) {
            this.$el.append($el.addClass("section-row").attr("id", id));
        }
    });

    exports.default = {
        View: View
    };
});
//# sourceMappingURL=../../../maps/mvc/form/form-section.js.map
