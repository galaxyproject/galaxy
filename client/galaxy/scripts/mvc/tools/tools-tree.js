/*
    This class maps the tool form to javascript datastructures. Once refreshed it converts the tool form (including sub sections) into a xml (containing only ids) and a detailed dictionary representation. The xml object is a jquery element and can be searched/filtered e.g. in order to hierarchically identify referenced fields. Once the job is ready for submission, the finalize function will transform the generic dictionary representation into the specific flat dictionary format required by the tools api.
*/
// dependencies
define([], function() {

// tool form tree
return Backbone.Model.extend({
    // initialize
    initialize: function(app) {
        // link app
        this.app = app;
    },
    
    /** Refresh the datastructures representing the ToolForm.
    */
    refresh: function() {
        // create dictionary
        this.dict = {};
        
        // create xml object
        this.xml = $('<div/>');
        
        // check if section is available
        if (!this.app.section) {
            return {};
        }
        
        // fill dictionary
        this._iterate(this.app.section.$el, this.dict, this.xml);
    },

    /** Convert dictionary representation into tool api specific flat dictionary format.
    */
    finalize: function(patch) {
        // initialize
        patch = patch || {};
        
        // link this
        var self = this;
        
        // dictionary formatted for job submission
        this.job_def = {};

        // dictionary with api specific identifiers
        this.job_ids = {};

        // add identifier and value to job definition
        function add(job_input_id, input_id, input_value) {
            self.job_def[job_input_id] = input_value;
            self.job_ids[job_input_id] = input_id;
        };

        // converter between raw dictionary and job dictionary
        function convert(identifier, head) {
            for (var index in head) {
                var node = head[index];
                if (node.input) {
                    // get node
                    var input = node.input;
                    
                    // create identifier
                    var job_input_id = identifier;
                    if (identifier != '') {
                        job_input_id += '|';
                    }
                    job_input_id += input.name;
                    
                    // process input type
                    switch (input.type) {
                        // handle repeats
                        case 'repeat':
                            // section identifier
                            var section_label = 'section-';
                            
                            // collect repeat block identifiers
                            var block_indices = [];
                            var block_prefix = null;
                            for (var block_label in node) {
                                var pos = block_label.indexOf(section_label);
                                if (pos != -1) {
                                    pos += section_label.length;
                                    block_indices.push(parseInt(block_label.substr(pos)));
                                    if (!block_prefix) {
                                        block_prefix = block_label.substr(0, pos);
                                    }
                                }
                            }
                            
                            // sort repeat blocks
                            block_indices.sort(function(a,b) { return a - b; });
                            
                            // add to response dictionary in created order
                            var index = 0;
                            for (var i in block_indices) {
                                convert(job_input_id + '_' + index++, node[block_prefix + block_indices[i]]);
                            }
                            break;
                        // handle conditionals
                        case 'conditional':
                            // get and patch conditional value
                            var value = self.app.field_list[input.id].value();
                            if (patch[input.test_param.type]) {
                                value = patch[input.test_param.type](value);
                            }
                            
                            // add conditional value
                            add (job_input_id + '|' + input.test_param.name, input.id, value);
                            
                            // identify selected case
                            var selectedCase = self.matchCase(input, value);
                            if (selectedCase != -1) {
                                convert(job_input_id, head[input.id + '-section-' + selectedCase]);
                            }
                            break;
                        default:
                            // get field
                            var field = self.app.field_list[input.id];
                            
                            // get and patch field value
                            var value = field.value();
                            if (patch[input.type]) {
                                value = patch[input.type](value);
                            }
                            
                            // handle default value
                            if (!field.skip) {
                                if (input.optional && field.validate && !field.validate()) {
                                    value = 'None';
                                }
                                add (job_input_id, input.id, value);
                            }
                    }
                }
            }
        }
        
        // start conversion
        convert('', this.dict);
        
        // return result
        return this.job_def;
    },
    
    /** Match job definition identifier to input element identifier
    */
    match: function (job_input_id) {
        return this.job_ids && this.job_ids[job_input_id];
    },
    
    /** Match conditional values to selected cases
    */
    matchCase: function(input, value) {
        // format value for boolean inputs
        if (input.test_param.type == 'boolean') {
            if (value == 'true') {
                value = input.test_param.truevalue || 'true';
            } else {
                value = input.test_param.falsevalue || 'false';
            }
        }
        
        // find selected case
        for (var i in input.cases) {
            if (input.cases[i].value == value) {
                return i;
            }
        }
        
        // selected case not found
        return -1;
    },
    
    /** Matches identifier from api model to input elements
    */
    matchModel: function(model, callback) {
        // final result dictionary
        var result = {};
        
        // link this
        var self = this;
        
        // search throughout response
        function search (id, head) {
            for (var i in head) {
                var node = head[i];
                var index = node.name;
                if (id != '') {
                    index = id + '|' + index;
                }
                switch (node.type) {
                    case 'repeat':
                        for (var j in node.cache) {
                            search (index + '_' + j, node.cache[j]);
                        }
                        break;
                    case 'conditional':
                        var value = node.test_param && node.test_param.value;
                        var selectedCase = self.matchCase(node, value);
                        if (selectedCase != -1) {
                            search (index, node.cases[selectedCase].inputs);
                        }
                        break;
                    default:
                        var input_id = self.app.tree.job_ids[index];
                        if (input_id) {
                            callback(input_id, node);
                        }
                }
            }
        }
        
        // match all ids and return messages
        search('', model.inputs);

        // return matched results
        return result;
    },
    
    /** Matches identifier from api response to input elements
    */
    matchResponse: function(response) {
        // final result dictionary
        var result = {};
        
        // link this
        var self = this;
        
        // search throughout response
        function search (id, head) {
            if (typeof head === 'string') {
                var input_id = self.app.tree.job_ids[id];
                if (input_id) {
                    result[input_id] = head;
                }
            } else {
                for (var i in head) {
                    var new_id = i;
                    if (id !== '') {
                        var separator = '|';
                        if (head instanceof Array) {
                            separator = '_';
                        }
                        new_id = id + separator + new_id;
                    }
                    search (new_id, head[i]);
                }
            }
        }
        
        // match all ids and return messages
        search('', response);
        
        // return matched results
        return result;
    },
    
    /** Find referenced elements.
    */
    references: function(identifier, type) {
        // referenced elements
        var referenced = [];
        
        // link this
        var self = this;
        
        // iterate
        function search (name, parent) {
            // get child nodes
            var children = $(parent).children();
            
            // create list of referenced elements
            var list = [];
            
            // a node level is skipped if a reference of higher priority was found
            var skip = false;
            
            // verify that hierarchy level is referenced by target identifier
            children.each(function() {
                // get child element
                var child = this;
                
                // get id
                var id = $(child).attr('id');
            
                // skip target element
                if (id !== identifier) {
                    // get input element
                    var input = self.app.input_list[id];
                    if (input) {
                        // check for new reference definition with higher priority
                        if (input.name == name) {
                            // skip iteration for this branch
                            skip = true;
                            return false;
                        }
                        
                        // check for referenced element
                        if (input.data_ref == name && input.type == type) {
                            list.push(id);
                        }
                    }
                }
            });
            
            // skip iteration
            if (!skip) {
                // merge temporary list with result
                referenced = referenced.concat(list);
                
                // continue iteration
                children.each(function() {
                    search(name, this);
                });
            }
        }
        
        // get initial node
        var node = this.xml.find('#' + identifier);
        if (node.length > 0) {
            // get parent input element
            var input = this.app.input_list[identifier];
            if (input) {
                search(input.name, node.parent());
            }
        }
        
        // return
        return referenced;
    },
    
    /** Iterate through the tool form dom and map it to the dictionary and xml representation.
    */
    _iterate: function(parent, dict, xml) {
        // get child nodes
        var self = this;
        var children = $(parent).children();
        children.each(function() {
            // get child element
            var child = this;
            
            // get id
            var id = $(child).attr('id');
            
            // create new branch
            if ($(child).hasClass('section-row')) {
                // create sub dictionary
                dict[id] = {};
                
                // add input element if it exists
                var input = self.app.input_list[id];
                if (input) {
                    dict[id] = {
                        input : input
                    }
                }
                
                // create xml element
                var $el = $('<div id="' + id + '"/>');
                
                // append xml
                xml.append($el);
                
                // fill sub dictionary
                self._iterate(child, dict[id], $el);
            } else {
                self._iterate(child, dict, xml);
            }
        });
    }
});

});