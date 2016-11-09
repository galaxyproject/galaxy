define([ "mvc/toolshed/toolshed-model" ], function(toolshed_model) {
    var ToolShedCategoryContentsView = Backbone.View.extend({
        el: "#center",
        initialize: function(shed, category) {
            console.log(arguments);
            this.model = new toolshed_model.CategoryCollection(), this.listenTo(this.model, "sync", this.render), 
            this.model.url += "?tool_shed_url=" + shed + "&category_id=" + category, this.model.tool_shed = shed, 
            this.model.category = category, this.model.fetch();
        },
        render: function(options) {
            console.log("render cat"), this.options = _.extend(this.options, options);
            var category_contents_template = this.templateCategoryContents;
            console.log(this.model.models), this.$el.html(category_contents_template({
                category: this.model.models[0],
                tool_shed: this.model.tool_shed
            })), $("#center").css("overflow", "auto");
        },
        templateCategoryContents: _.template([ '<div class="tab-pane" id="list_repositories">', '<div id="standard-search" style="height: 2em; margin: 1em;">', '<span class="ui-widget" >', '<input class="search-box-input" id="category_search" name="search" placeholder="Search repositories by name or id" size="60" type="text" />', "</span>", "</div>", '<div style="clear: both; margin-top: 1em;">', '<h2>Repositories in <%= category.get("name") %></h2>', '<table class="grid">', '<thead id="grid-table-header">', "<tr>", '<th style="width: 10%;">Owner</th>', '<th style="width: 15%;">Name</th>', "<th>Synopsis</th>", '<th style="width: 10%;">Type</th>', "</tr>", "</thead>", '<% _.each(category.get("repositories"), function(repository) { %>', "<tr>", "<td><%= repository.owner %></td>", "<td>", '<a href="#/repository/s/<%= tool_shed %>/r/<%= repository.id %>"><%= repository.name %></a>', "</td>", "<td><%= repository.description %></td>", "<td><%= repository.type %></td>", "</tr>", "<% }); %>", "</table>", "</div>", "</div>" ].join(""))
    });
    return {
        Category: ToolShedCategoryContentsView
    };
});