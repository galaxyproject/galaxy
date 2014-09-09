// dependencies
define([], function() {

// tool form tree
return Backbone.Model.extend({
    // initialize
    initialize: function(app) {
        // link app
        this.app = app;
    },
    
    // creates tree structure
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

    // convert to job dictionary
    finalize: function() {
        // link this
        var self = this;
        
        // dictionary formatted for job submission
        var job_def = {};

        // converter between raw dictionary and job dictionary
        function convert(identifier, head) {
            for (var i in head) {
                var node = head[i];
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
                            var index = 0;
                            for (var j in node) {
                                if (j.indexOf('section') != -1) {
                                    convert(job_input_id + '_' + index++, node[j]);
                                }
                            }
                            break;
                        // handle conditionals
                        case 'conditional':
                            // get conditional value
                            var value = self.app.field_list[input.id].value();
                            
                            // find selected case
                            for (var j in input.cases) {
                                if (input.cases[j].value == value) {
                                    convert(job_input_id, head[input.id + '-section-' + j]);
                                    break;
                                }
                            }
                            
                            // break
                            break;
                        default:
                            // handle default value
                            var value = self.app.field_list[input.id].value();
                            job_def[job_input_id] = value;
                    }
                }
            }
        }
        
        // start conversion
        convert('', this.dict);
       
        // return result
        return job_def;
    },
    
    // find referenced elements
    findReferences: function(identifier, type) {
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
    
    // iterate
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
            if ($(child).hasClass('section-row') || $(child).hasClass('tab-pane')) {
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