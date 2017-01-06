define([ "mvc/toolshed/toolshed-model", "mvc/toolshed/util" ], function(toolshed_model, toolshed_util) {
    var ToolShedCategoryContentsView = Backbone.View.extend({
        el: "#center",
        initialize: function(params) {
            this.model = new toolshed_model.CategoryCollection(), this.listenTo(this.model, "sync", this.render);
            var shed = params.tool_shed.replace(/\//g, "%2f");
            this.model.url += "?tool_shed_url=" + shed + "&category_id=" + params.category_id, 
            this.model.tool_shed = shed, this.model.category = params.category_id, this.model.fetch();
        },
        render: function(options) {
            this.options = _.extend(this.options, options);
            var category_contents_template = this.templateCategoryContents;
            this.$el.html(category_contents_template({
                category: this.model.models[0],
                tool_shed: this.model.tool_shed
            })), $("#center").css("overflow", "auto"), this.bindEvents();
        },
        bindEvents: function() {
            console.log("that.selector"), require([ "libs/jquery/jquery-ui" ], function() {
                $("search_box").autocomplete({
                    source: function(req) {
                        console.log("blop" + req);
                    },
                    minLength: 3,
                    select: function(event, ui) {
                        var tsr_id = ui.item.value, api_url = Galaxy.root + "api/tool_shed/repository", params = {
                            tool_shed_url: this.model.tool_shed,
                            tsr_id: tsr_id
                        };
                        toolshed_util.loadRepo(tsr_id, this.model.tool_shed, api_url, params);
                    }
                });
            });
        },
        reDraw: function(options) {
            this.$el.empty(), this.initialize(options);
        },
        templateCategoryContents: _.template([ '<div class="unified-panel-header" unselectable="on">', '<div class="unified-panel-header-inner">Repositories in <%= category.get("name") %></div>', "</div>", '<div class="unified-panel-body" id="list_repositories">', '<div id="standard-search" style="height: 2em; margin: 1em;">', '<span class="ui-widget" >', '<input class="search-box-input" id="search_box" name="search" data-shedurl="<%= tool_shed.replace(/%2f/g, "/") %>" placeholder="Search repositories by name or id" size="60" type="text" />', "</span>", "</div>", '<div style="clear: both; margin-top: 1em;">', '<table class="grid">', '<thead id="grid-table-header">', "<tr>", '<th style="width: 10%;">Owner</th>', '<th style="width: 15%;">Name</th>', "<th>Synopsis</th>", '<th style="width: 10%;">Type</th>', "</tr>", "</thead>", '<% _.each(category.get("repositories"), function(repository) { %>', "<tr>", "<td><%= repository.owner %></td>", "<td>", '<div style="float: left; margin-left: 1px;" class="menubutton split">', '<a href="#/repository/s/<%= tool_shed %>/r/<%= repository.id %>"><%= repository.name %></a>', "</div>", "</td>", "<td><%= repository.description %></td>", "<td><%= repository.type %></td>", "</tr>", "<% }); %>", "</table>", "</div>", "</div>" ].join(""))
    });
    return {
        Category: ToolShedCategoryContentsView
    };
});