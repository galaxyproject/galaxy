/**
    This class creates a tool form section and populates it with input elements. It also handles repeat blocks and conditionals by recursively creating new sub sections.
*/
define(['utils/utils',
        'mvc/ui/ui-table',
        'mvc/ui/ui-misc',
        'mvc/ui/ui-portlet',
        'mvc/tools/tools-repeat',
        'mvc/tools/tools-input',
        'mvc/tools/tools-parameters'],
    function(Utils, Table, Ui, Portlet, Repeat, InputElement, Parameters) {

    // create form view
    var View = Backbone.View.extend({
        // initialize
        initialize: function(app, options) {
            // link app
            this.app = app;

            // link inputs
            this.inputs = options.inputs;

            // fix table style
            options.cls = 'ui-table-plain';

            // add table class for tr tag
            // this assist in transforming the form into a json structure
            options.cls_tr = 'section-row';
            
            // create table
            this.table = new Table.View(options);
            
            // create parameter handler
            this.parameters = new Parameters(app, options);

            // configure portlet and form table
            this.setElement(this.table.$el);

            // render tool section
            this.render();
        },

        /** Render section view
        */
        render: function() {
            // reset table
            this.table.delAll();

            // load settings elements into table
            for (var i in this.inputs) {
                this.add(this.inputs[i]);
            }
        },

        /** Add a new input element
        */
        add: function(input) {
            // link this
            var self = this;

            // clone definition
            var input_def = jQuery.extend(true, {}, input);

            // create unique id
            input_def.id = input.id = Utils.uuid();

            // add to sequential list of inputs
            this.app.input_list[input_def.id] = input_def;

            // identify field type
            var type = input_def.type;
            switch(type) {
                // conditional field
                case 'conditional':
                    this._addConditional(input_def);
                    break;
                // repeat block
                case 'repeat':
                    this._addRepeat(input_def);
                    break;
                // customized section
                case 'section':
                    this._addSection(input_def);
                    break;
                // default single element row
                default:
                    this._addRow(input_def);
            }
        },

        /** Add a conditional block
        */
        _addConditional: function(input_def) {
            // link this
            var self = this;

            // copy identifier
            input_def.test_param.id = input_def.id;

            // build test parameter
            var field = this._addRow(input_def.test_param);

            // set onchange event for test parameter
            field.options.onchange = function(value) {
                // identify the selected case
                var selectedCase = self.app.tree.matchCase(input_def, value);

                // check value in order to hide/show options
                for (var i in input_def.cases) {
                    // get case
                    var case_def = input_def.cases[i];

                    // identify subsection name
                    var section_id = input_def.id + '-section-' + i;

                    // identify row
                    var section_row = self.table.get(section_id);

                    // check if non-hidden elements exist
                    var nonhidden = false;
                    for (var j in case_def.inputs) {
                        if (!case_def.inputs[j].hidden) {
                            nonhidden = true;
                            break;
                        }
                    }

                    // show/hide sub form
                    if (i == selectedCase && nonhidden) {
                        section_row.fadeIn('fast');
                    } else {
                        section_row.hide();
                    }
                }

                // refresh form inputs
                self.app.trigger('refresh');
            };

            // add conditional sub sections
            for (var i in input_def.cases) {
                // create id tag
                var sub_section_id = input_def.id + '-section-' + i;

                // create sub section
                var sub_section = new View(this.app, {
                    inputs  : input_def.cases[i].inputs
                });

                // displays as grouped subsection
                sub_section.$el.addClass('ui-table-section');

                // create table row
                this.table.add(sub_section.$el);

                // append to table
                this.table.append(sub_section_id);
            }

            // trigger refresh on conditional input field after all input elements have been created
            field.trigger('change');
        },

        /** Add a repeat block
        */
        _addRepeat: function(input_def) {
            // link this
            var self = this;

            // block index
            var block_index = 0;

            // create repeat block element
            var repeat = new Repeat.View({
                title           : input_def.title,
                title_new       : input_def.title,
                min             : input_def.min,
                max             : input_def.max,
                onnew           : function() {
                    // create
                    create(input_def.inputs);
                            
                    // trigger refresh
                    self.app.trigger('refresh');
                }
            });

            // helper function to create new repeat blocks
            function create (inputs) {
                // create id tag
                var sub_section_id = input_def.id + '-section-' + (block_index++);

                // create sub section
                var sub_section = new View(self.app, {
                    inputs  : inputs
                });

                // add tab
                repeat.add({
                    id      : sub_section_id,
                    $el     : sub_section.$el,
                    ondel   : function() {
                        // delete repeat block
                        repeat.del(sub_section_id);
                        
                        // trigger refresh
                        self.app.trigger('refresh');
                    }
                });
            }

            //
            // add parsed/minimum number of repeat blocks
            //
            var n_min   = input_def.min;
            var n_cache = _.size(input_def.cache);
            for (var i = 0; i < Math.max(n_cache, n_min); i++) {
                var inputs = null;
                if (i < n_cache) {
                    inputs = input_def.cache[i];
                } else {
                    inputs = input_def.inputs;
                }

                // create repeat block
                create(inputs);
            }

            // create input field wrapper
            var input_element = new InputElement(this.app, {
                label   : input_def.title,
                help    : input_def.help,
                field   : repeat
            });

            // create table row
            this.table.add(input_element.$el);

            // append row to table
            this.table.append(input_def.id);
        },

        /** Add a customized section
        */
        _addSection: function(input_def) {
            // link this
            var self = this;
            
            // create sub section
            var sub_section = new View(self.app, {
                inputs  : input_def.inputs
            });

            // delete button
            var button_visible = new Ui.ButtonIcon({
                icon    : 'fa-eye-slash',
                tooltip : 'Show/hide section',
                cls     : 'ui-button-icon-plain'
            });

            // create portlet for sub section
            var portlet = new Portlet.View({
                title       : input_def.label,
                cls         : 'ui-portlet-section',
                operations  : {
                    button_visible: button_visible
                }
            });
            portlet.append(sub_section.$el);
            portlet.append($('<div/>').addClass('ui-table-form-info').html(input_def.help));

            // add event handler visibility button
            var visible = false;
            portlet.$content.hide();
            portlet.$header.css('cursor', 'pointer');
            portlet.$header.on('click', function() {
                if (visible) {
                    visible = false;
                    portlet.$content.hide();
                    button_visible.setIcon('fa-eye-slash');
                } else {
                    visible = true;
                    portlet.$content.fadeIn('fast');
                    button_visible.setIcon('fa-eye');
                }
            });

            // show sub section if requested
            if (input_def.expand) {
                portlet.$header.trigger('click');
            }

            // create table row
            this.table.add(portlet.$el);

            // append row to table
            this.table.append(input_def.id);
        },

        /** Add a single input field element
        */
        _addRow: function(input_def) {
            // get id
            var id = input_def.id;

            // create input field
            var field = this.parameters.create(input_def);

            // add to field list
            this.app.field_list[id] = field;

            // create input field wrapper
            var input_element = new InputElement(this.app, {
                label           : input_def.label,
                default_value   : input_def.default_value,
                optional        : input_def.optional,
                help            : input_def.help,
                field           : field
            });

            // add to element list
            this.app.element_list[id] = input_element;

            // create table row
            this.table.add(input_element.$el);

            // append to table
            this.table.append(id);

            // hide row if neccessary
            if (input_def.hidden) {
                this.table.get(id).hide();
            }

            // return created field
            return field;
        }
    });

    return {
        View: View
    };
});
