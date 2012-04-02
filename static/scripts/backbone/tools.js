/**
 * Model classes for Galaxy tools and tool panel. Models have no references to views,
 * instead using events to indicate state changes; this is advantageous because
 * multiple views can use the same object and models can be used without views.
 */
 
/**
 * Simple base model for any visible element. Includes useful attributes and ability 
 * to set and track visibility.
 */
var BaseModel = Backbone.Model.extend({
    defaults: {
        id: null,
        name: null,
        hidden: false
    },
    
    show: function() {
        this.set("hidden", false);
    },
    
    hide: function() {
        this.set("hidden", true);
    },
    
    is_visible: function() {
        return !this.attributes.hidden;
    }
});

/**
 * A Galaxy tool.
 */
var Tool = BaseModel.extend({
    // Default attributes.
    defaults: {
        description: null,
        target: null,
        params: []
    },
    
    apply_search_results: function(results) {
        ( _.indexOf(results, this.attributes.id) !== -1 ? this.show() : this.hide() );
        return this.is_visible();
    }
});

/**
 * Label or section header in tool panel.
 */
var ToolPanelLabel = BaseModel.extend({});

/**
 * Section of tool panel with elements (labels and tools).
 */
var ToolPanelSection = BaseModel.extend({
    defaults: {
        elems: [],
        open: false
    },
    
    clear_search_results: function() {
        _.each(this.attributes.elems, function(elt) {
            elt.show();
        });
        
        this.show();
        this.set("open", false);
    },
    
    apply_search_results: function(results) {
        var all_hidden = true,
            cur_label;
        _.each(this.attributes.elems, function(elt) {            
            if (elt instanceof ToolPanelLabel) {
                cur_label = elt;
                cur_label.hide();
            }
            else if (elt instanceof Tool) {
                if (elt.apply_search_results(results)) {
                    all_hidden = false;
                    if (cur_label) {
                        cur_label.show();
                    }
                }
            }
        });
        
        if (all_hidden) {
            this.hide();
        }
        else {
            this.show();
            this.set("open", true);
        }
    }
});

/**
 * Tool search that updates results when query is changed. Result value of null
 * indicates that query was not run; if not null, results are from search using
 * query.
 */
var ToolSearch = Backbone.Model.extend({
    defaults: {
        spinner_url: "",
        search_url: "",
        visible: true,
        query: "",
        results: null
    },
    
    initialize: function() {
        this.on("change:query", this.do_search);
    },
    
    /**
     * Do the search and update the results.
     */
    do_search: function() {
        var query = this.attributes.query;
        
        // If query is too short, do not search.
        if (query.length < 3) {
            this.set("results", null);
            return;
        }
        
        // Do search via AJAX.
        var q = query + '*';
        // Stop previous ajax-request
        if (this.timer) {
            clearTimeout(this.timer);
        }
        // Start a new ajax-request in X ms
        $("#search-spinner").show();
        var self = this;
        this.timer = setTimeout(function () {
            $.get(self.attributes.search_url, { query: q }, function (data) {
                self.set("results", data);
                $("#search-spinner").hide();
            }, "json" );
        }, 200 );
    }
});

/**
 * A collection of ToolPanelSections, Tools, and ToolPanelLabels. Collection
 * applies search results as they become available.
 */
var ToolPanel = Backbone.Collection.extend({
    url: "/tools",
    parse: function(response) {
        // Recursive function to parse tool panel elements.
        var parse_elt = function(elt_dict) {
            var type = elt_dict.type;
            if (type === 'tool') {
                return new Tool(elt_dict);
            }
            else if (type === 'section') {
                // Parse elements.
                var elems = _.map(elt_dict.elems, parse_elt);
                elt_dict.elems = elems;
                return new ToolPanelSection(elt_dict);
            }
            else if (type === 'label') {
                return new ToolPanelLabel(elt_dict);
            }  
        };
        
        return _.map(response, parse_elt);
    },
    
    initialize: function(options) {
        this.tool_search = options.tool_search;
        this.tool_search.on("change:results", this.apply_search_results, this);
    },
    
    clear_search_results: function() {
        this.each(function(panel_elt) {
            panel_elt.clear_search_results();
        });
    },
    
    apply_search_results: function() {
        var results = this.tool_search.attributes.results;
        if (results === null) {
            this.clear_search_results();
            return;
        }
        
        this.each(function(panel_elt) {
            panel_elt.apply_search_results(results);
        });
    }
});

/**
 * View classes for Galaxy tools and tool panel. 
 * 
 * Views use precompiled Handlebars templates for rendering. Views update as needed
 * based on (a) model/collection events and (b) user interactions; in this sense,
 * they are controllers are well and the HTML is the real view in the MVC architecture.
 */
 
// TODO: implement a BaseModelView for handling model visibility.
 
/**
 * Link to a tool.
 */
var ToolLinkView = Backbone.View.extend({
    tagName: 'div',
    template: Handlebars.templates.tool_link,
    initialize: function() {
        this.model.on("change:hidden", this.update_visible, this);
    },
    render: function() {
        this.$el.append( this.template(this.model.toJSON()) );
        return this;
    },
    update_visible: function() {
        ( this.model.attributes.hidden ? this.$el.hide() : this.$el.show() );
    }
});

/**
 * Panel label/section header.
 */
var ToolPanelLabelView = Backbone.View.extend({
    tagName: 'div',
    className: 'toolPanelLabel',
    template: Handlebars.templates.panel_label,
    initialize: function() {
        this.model.on("change:hidden", this.update_visible, this);
    },
    render: function() {
        this.$el.append( this.template(this.model.toJSON()) );
        return this;
    },
    update_visible: function() {
        ( this.model.attributes.hidden ? this.$el.hide() : this.$el.show() );
    }
});

/**
 * Panel section.
 */
var ToolPanelSectionView = Backbone.View.extend({
    tagName: 'div',
    className: 'toolSectionWrapper',
    template: Handlebars.templates.panel_section,
    initialize: function() {
        this.model.on("change:hidden", this.update_visible, this);
        this.model.on("change:open", this.update_open, this);
    },
    render: function() {
        // Build using template.
        this.$el.append( this.template(this.model.toJSON()) );
        
        // Add tools to section.
        var section_body = this.$el.find(".toolSectionBody");
        _.each(this.model.attributes.elems, function(elt) {
            if (elt instanceof Tool) {
                var tool_view = new ToolLinkView({model: elt, className: "toolTitle"});
                tool_view.render();
                section_body.append(tool_view.$el);
            }
            else if (elt instanceof ToolPanelLabel) {
                var label_view = new ToolPanelLabelView({model: elt});
                label_view.render();
                section_body.append(label_view.$el);
            }
            else {
                // TODO: handle nested section bodies?
            }
        });
        return this;
    },
    
    events: {
        'click .toolSectionTitle > a': 'toggle'
    },
    
    /** 
     * Toggle visibility of tool section.
     */
    toggle: function() {
        this.$el.children(".toolSectionBody").toggle("fast");
        this.model.set("open", !this.model.attributes.open);
    },
    
    /**
     * Update whether section is open or close.
     */
    update_open: function() {
        (this.model.attributes.open ?
            this.$el.children(".toolSectionBody").show("fast") :
            this.$el.children(".toolSectionBody").hide("fast") 
        );
    },
    
    /**
     * Update section and section elements visibility after search.
     */
    update_visible: function() {
        ( this.model.attributes.hidden ? this.$el.hide() : this.$el.show() );
    }
});

var ToolSearchView = Backbone.View.extend({
    tagName: 'div',
    id: 'tool-search',
    className: 'bar',
    template: Handlebars.templates.tool_search,
    
    events: {
        'click': 'focus_and_select',
        'keyup :input': 'query_changed'
    },
    
    render: function() {
        this.$el.append( this.template(this.model.toJSON()) );
        return this;
    },
    
    focus_and_select: function() {
        this.$el.find(":input").focus().select();
    },
    
    query_changed: function() {
        this.model.set("query", this.$el.find(":input").val());
    }
});

var ToolPanelView = Backbone.View.extend({
    tagName: 'div',
    className: 'toolMenu',
    
    /**
     * Waits for collection to load and then renders.
     */
    initialize: function(options) {
        this.collection.tool_search.on("change:results", this.handle_search_results, this);
    },
    
    render: function() {
        var this_el = this.$el;
        
        // Render search.
        var search_view = new ToolSearchView( {model: this.collection.tool_search} );
        search_view.render();
        this_el.append(search_view.$el);
        
        // Render panel.
        this.collection.each(function(panel_elt) {
            if (panel_elt instanceof ToolPanelSection) {
                var section_title_view = new ToolPanelSectionView({model: panel_elt});
                section_title_view.render();
                this_el.append(section_title_view.$el);
            }
            else if (panel_elt instanceof Tool) {
                var tool_view = new ToolLinkView({model: elt, className: "toolTitleNoSection"});
                tool_view.render();
                this_el.append(tool_view.$el);
            }
        });
        return this;
    },
    
    handle_search_results: function() {
        var results = this.collection.tool_search.attributes.results;
        if (results && results.length === 0) {
            $("#search-no-results").show();
        }
        else {
            $("#search-no-results").hide();
        }
    }
});
