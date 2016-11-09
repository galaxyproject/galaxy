define([ "mvc/toolshed/toolshed-model" ], function(toolshed_model) {
    var ToolShedCategories = Backbone.View.extend({
        el: "#center",
        initialize: function(shed) {
            console.log(arguments);
            this.model = new toolshed_model.Categories(), this.listenTo(this.model, "sync", this.render), 
            this.model.url += "?tool_shed_url=" + shed, this.model.tool_shed = shed.replace(/\//g, "%2f"), 
            this.model.fetch();
        },
        render: function(options) {
            console.log("render cat"), this.options = _.extend(this.options, options);
            var category_list_template = this.templateCategoryList;
            console.log(this.model), this.$el.html(category_list_template({
                categories: this.model.models,
                tool_shed: this.model.tool_shed
            })), $("#center").css("overflow", "auto");
        },
        templateCategoryList: _.template([ "<% console.log(arguments); %>", '<div class="tab-pane" id="list_categories" style="overflow: scroll;">', '<div id="standard-search" style="height: 2em; margin: 1em;">', '<span class="ui-widget" >', '<input class="search-box-input" id="repository_search" name="search" placeholder="Search repositories by name or id" size="60" type="text" />', "</span>", "</div>", '<div style="clear: both; margin-top: 1em;">', "<h2>Repositories by Category</h2>", '<table class="grid">', '<thead id="grid-table-header">', "<tr>", "<th>Name</th>", "<th>Description</th>", "<th>Repositories</th>", "</tr>", "</thead>", "<% _.each(categories, function(category) { %>", "<tr>", "<td>", '<a href="#/category/s/<%= tool_shed %>/c/<%= category.get("id") %>"><%= category.get("name") %></a>', "</td>", '<td><%= category.get("description") %></td>', '<td><%= category.get("repositories") %></td>', "</tr>", "<% }); %>", "</table>", "</div>", "</div>" ].join(""))
    });
    return {
        CategoryView: ToolShedCategories
    };
});