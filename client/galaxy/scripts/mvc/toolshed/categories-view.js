define(['mvc/toolshed/toolshed-model', 'mvc/toolshed/util'], function(toolshed_model, toolshed_util) {

    var ToolShedCategories = Backbone.View.extend({

        el: '#center',

        defaults: {
            tool_shed: "https://toolshed.g2.bx.psu.edu/"
        },

        initialize: function(options) {
            var self = this;
            this.options = _.defaults(this.options || options, this.defaults);
            this.model = new toolshed_model.Categories();
            this.listenTo(this.model, 'sync', this.render);
            this.model.url = this.model.url + '?tool_shed_url=' + this.options.tool_shed;
            this.model.fetch();
        },

        render: function(options) {
            this.options = _.extend(this.options, options);
            this.options.categories = this.model.models;
            var category_list_template = this.templateCategoryList;
            this.$el.html(category_list_template(this.options));
            $("#center").css('overflow', 'auto');
            this.bindEvents();
        },

        bindEvents: function() {
            // toolshed_util.initSearch('search_box');
        },

        reDraw: function(options) {
            this.$el.empty();
            this.model.url = this.model.url + '?tool_shed_url=' + this.options.tool_shed;
            this.initialize(options);
            // this.model.fetch();
            // this.render(options);
        },

        templateCategoryList: _.template([
            '<div class="unified-panel-header" unselectable="on">',
                '<div class="unified-panel-header-inner" style="layout: inline;">Categories in <%= tool_shed.replace(/%2f/g, "/") %></div>',
            '</div>',
            '<div class="unified-panel-body" id="list_categories">',
                '<div id="standard-search" style="height: 2em; margin: 1em;">',
                    '<span class="ui-widget" >',
                        '<input class="search-box-input" id="search_box" data-shedurl="<%= tool_shed.replace(/%2f/g, "/") %>" name="search" placeholder="Search repositories by name or id" size="60" type="text" />',
                    '</span>',
                '</div>',
                '<div style="clear: both; margin-top: 1em;">',
                    '<table class="grid">',
                        '<thead id="grid-table-header">',
                            '<tr>',
                                '<th>Name</th>',
                                '<th>Description</th>',
                                '<th>Repositories</th>',
                            '</tr>',
                        '</thead>',
                        '<% _.each(categories, function(category) { %>',
                            '<tr>',
                                '<td>',
                                    '<a href="#/category/s/<%= tool_shed %>/c/<%= category.get("id") %>"><%= category.get("name") %></a>',
                                '</td>',
                                '<td><%= category.get("description") %></td>',
                                '<td><%= category.get("repositories") %></td>',
                            '</tr>',
                        '<% }); %>',
                    '</table>',
                '</div>',
            '</div>',
        ].join(''))
    });

    return {
        CategoryView: ToolShedCategories,
    };

});