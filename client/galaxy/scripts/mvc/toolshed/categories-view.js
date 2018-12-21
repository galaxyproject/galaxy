import _ from "underscore";
import $ from "jquery";
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import toolshed_model from "mvc/toolshed/toolshed-model";
import toolshed_util from "mvc/toolshed/util";
import "libs/jquery/jquery-ui";

var ToolShedCategories = Backbone.View.extend({
    el: "#center",

    defaults: {
        tool_shed: "https://toolshed.g2.bx.psu.edu/"
    },

    initialize: function(options) {
        var shed = options.tool_shed.replace(/\//g, "%2f");
        this.options = _.defaults(this.options || options, this.defaults);
        this.model = new toolshed_model.Categories();
        this.listenTo(this.model, "sync", this.render);
        this.model.url = `${this.model.url}?tool_shed_url=${this.options.tool_shed}`;
        this.model.tool_shed = shed;
        this.model.fetch();
    },

    render: function(options) {
        this.options = _.extend(this.options, options);
        this.options.categories = this.model.models;
        this.options.queue = toolshed_util.queueLength();
        var category_list_template = this.templateCategoryList;
        this.$el.html(category_list_template(this.options));
        $("#center").css("overflow", "auto");
        this.bindEvents();
    },

    bindEvents: function() {
        $("#search_box").autocomplete({
            source: (request, response) => {
                var shed_url = this.model.tool_shed.replace(/%2f/g, "/");
                var base_url = `${getAppRoot()}api/tool_shed/search`;
                var params = {
                    term: request.term,
                    tool_shed_url: shed_url
                };
                $.post(base_url, params, data => {
                    console.log(data);
                    var result_list = toolshed_util.shedParser(data);
                    response(result_list);
                });
            },
            minLength: 3,
            select: (event, ui) => {
                var tsr_id = ui.item.value;
                var new_route = `repository/s/${this.model.tool_shed}/r/${tsr_id}`;
                Backbone.history.navigate(new_route, {
                    trigger: true,
                    replace: true
                });
            }
        });
    },

    templateCategoryList: _.template(
        [
            '<style type="text/css">',
            ".ui-autocomplete { background-color: #fff; }",
            "li.ui-menu-item { list-style-type: none; }",
            "</style>",
            '<div class="unified-panel-header" id="panel_header" unselectable="on">',
            '<div class="unified-panel-header-inner" style="layout: inline;">Categories in <%= tool_shed.replace(/%2f/g, "/") %><a class="ml-auto" href="#/queue">Repository Queue (<%= queue %>)</a></div>',
            "</div>",
            '<div class="unified-panel-body" id="list_categories">',
            '<div id="standard-search" style="height: 2em; margin: 1em;">',
            '<span class="ui-widget" >',
            '<input class="search-box-input" id="search_box" data-shedurl="<%= tool_shed.replace(/%2f/g, "/") %>" name="search" placeholder="Search repositories by name or id" size="60" type="text" />',
            "</span>",
            "</div>",
            '<div style="clear: both; margin-top: 1em;">',
            '<table class="grid">',
            '<thead id="grid-table-header">',
            "<tr>",
            "<th>Name</th>",
            "<th>Description</th>",
            "<th>Repositories</th>",
            "</tr>",
            "</thead>",
            "<% _.each(categories, function(category) { %>",
            "<tr>",
            "<td>",
            '<a href="#/category/s/<%= tool_shed %>/c/<%= category.get("id") %>"><%= category.get("name") %></a>',
            "</td>",
            '<td><%= category.get("description") %></td>',
            '<td><%= category.get("repositories") %></td>',
            "</tr>",
            "<% }); %>",
            "</table>",
            "</div>",
            "</div>"
        ].join("")
    )
});

export default {
    CategoryView: ToolShedCategories
};
