import * as Backbone from "backbone";
import * as _ from "underscore";

import toolshed_model from "mvc/toolshed/toolshed-model";
import toolshed_util from "mvc/toolshed/util";
import "libs/jquery/jquery-ui";

/* global $ */
/* global Galaxy */

var ToolShedCategoryContentsView = Backbone.View.extend({
    el: "#center",

    initialize: function(params) {
        this.params = params;
        this.model = new toolshed_model.CategoryCollection();
        this.listenTo(this.model, "sync", this.render);
        var shed = params.tool_shed.replace(/\//g, "%2f");
        this.model.url += `?tool_shed_url=${shed}&category_id=${params.category_id}&sort_key=${params.sort_key}&sort_order=${params.sort_order}&page=${params.page}`;
        this.model.tool_shed = shed;
        this.model.category = params.category_id;
        this.model.fetch();
    },

    render: function(options) {
        this.options = _.defaults(this.options || {}, options);
        var category_contents_template = this.templateCategoryContents;
        var page_navigation_template = this.templatePageNavigation;
        var sorting = {class: {owner: 'fa-sort', description: 'fa-sort', name: 'fa-sort'},
                       direction: {owner: 'asc', description: 'asc', name: 'asc'}};
        sorting.class[this.params.sort_key] = (this.params.sort_order == 'desc' ? 'fa-sort-down' : 'fa-sort-up');
        sorting.direction[this.params.sort_key] = (this.params.sort_order == 'asc' ? 'desc' : 'asc');
        var current_page = this.params.page;
        var previous_page = Math.max(this.params.page - 1, 1);
        var pages = parseInt((this.model.models[0].get('repository_count')) % 25) + 1;
        var next_page = Math.min(parseInt(this.params.page) + 1, pages);
        var pagination_params = {
            page: this.params.page,
            next: next_page,
            previous: previous_page,
            pages: pages};
        if (pages > 5) {
            var page = parseInt(this.params.page);
            var page_slice = Array();
            var slice_start = Math.max(page - 2, 2);
            var i = slice_start;
            var slice_end = Math.min(Math.min(page + 2, slice_start + 4), pages);
            for (i = slice_start; i <= slice_end; i++) {
                page_slice.push(i);
            }
            pagination_params['page_slice'] = page_slice;
        }
        this.$el.html(
            category_contents_template({
                page_navigation: page_navigation_template(pagination_params),
                category: this.model.models[0],
                tool_shed: this.model.tool_shed,
                queue: toolshed_util.queueLength(),
                sorting: sorting,
                page: this.params.page
            })
        );
        $("#center").css("overflow", "auto");
        this.bindEvents();
    },

    bindEvents: function() {
        $("#search_box").autocomplete({
            source: (request, response) => {
                var shed_url = this.model.tool_shed.replace(/%2f/g, "/");
                var base_url = `${Galaxy.root}api/tool_shed/search`;
                var params = {
                    term: request.term,
                    tool_shed_url: shed_url
                };
                $.post(base_url, params, data => {
                    var result_list = toolshed_util.shedParser(data);
                    response(result_list);
                });
            },
            minLength: 3,
            select: function(event, ui) {
                var tsr_id = ui.item.value;
                var new_route = `repository/s/${this.model.tool_shed}/r/${tsr_id}`;
                Backbone.history.navigate(new_route, {
                    trigger: true,
                    replace: true
                });
            }
        });
        $('.fa-fw').on("click", (ev) => {
            var parameters = {};
            parameters.field = $(ev.target).attr('data-field');
            parameters.direction = $(ev.target).attr('data-direction');
            var new_route = `category/s/${this.model.tool_shed}/c/${this.model.category}/k/${parameters.field}/p/${this.params.page}/t/${parameters.direction}`
            Backbone.history.navigate(new_route, {
                trigger: true,
                replace: true
            });
        });
        $('.pagenav').on("click", (ev) => {
            var page = $(ev.target).attr('data-page');
            var new_route = `category/s/${this.model.tool_shed}/c/${this.model.category}/k/${this.params.sort_key}/p/${page}/t/${this.params.sort_order}`;
            Backbone.history.navigate(new_route, {
                trigger: true,
                replace: true
            });
        });
    },

    templatePageNavigation: _.template(
        [
            '<div class="navigation">',
            "<% if (page != 1) { %>",
            '<a data-page="1" class="pagenav fa fa-fast-backward" />',
            '<a data-page="<%= previous %>" class="pagenav fa fa-step-backward" />',
            "<% } else { %>",
            '<a data-page="1" class="pagenav-inactive fa fa-fast-backward" />',
            '<a data-page="<%= previous %>" class="pagenav-inactive fa fa-step-backward" />',
            '<% } %>',
            '<% if (pages > 5) { %>',
            '<% if (page != 1) { %>',
            '<a data-page="1" class="pagenav fa"><a>1</a>',
            '<% if (page != 2) { %>',
            '<a class="fa">&hellip;</a>',
            '<% } %>',
            '<% } else { %>',
            '<a data-page="1" class="pagenav-inactive fa"><a>1</a>',
            '<% } %>',
            '<% _.each(page_slice, function(i) { %>',
            '<% if (i == page) { %>',
            '<a data-page="<%= i %>" class="fa"><strong><%= i %></strong></a>',
            '<% } else { %>',
            '<a data-page="<%= i %>" class="pagenav fa"><%= i %></a>',
            '<% } %>',
            '<% }); %>',
            '<% var last_pages = [pages - 2, pages - 1, pages]; %>',
            '<% if (last_pages.indexOf(parseInt(page)) == -1) { %>',
            '<a class="fa">&hellip;</a>',
            '<a data-page="<%= pages %>" class="pagenav fa"><%= pages %></a>',
            '<% } %>',
            '<% } else { %>',
            '<% for (i = 1; i <= pages; i++) { %>',
            '<% if (i == page) { %>',
            '<a data-page="<%= i %>" class="fa"><strong><%= i %></strong></a>',
            '<% } else { %>',
            '<a data-page="<%= i %>" class="pagenav fa"><%= i %></a>',
            '<% } %>',
            '<% } %>',
            '<% } %>',
            '<% if (page < pages) { %>',
            '<a data-page="<%= next %>" class="pagenav fa fa-step-forward" />',
            '<a data-page="<%= pages %>" class="pagenav fa fa-fast-forward" />',
            "<% } else { %>",
            '<a data-page="<%= next %>" class="pagenav-inactive fa fa-step-forward" />',
            '<a data-page="<%= pages %>" class="pagenav-inactive fa fa-fast-forward" />',
            '<% } %>',
            '</div>'
        ].join("")
    ),

    templateCategoryContents: _.template(
        [
            '<style type="text/css">',
            ".ui-autocomplete { background-color: #fff; }",
            "li.ui-menu-item { list-style-type: none; }",
            "div.navigation { width: 100%; text-align: center; }",
            "div.navigation a { margin-left: 0.5em; margin-right: 0.5em; display: inline; text-decoration: underline; }",
            "a.pagenav-inactive { opacity: 0.5; }",
            "</style>",
            '<div class="unified-panel-header" id="panel_header" unselectable="on">',
            '<div class="unified-panel-header-inner">Repositories in <%= category.get("name") %><a class="ml-auto" href="#/queue">Repository Queue (<%= queue %>)</a></div>',
            "</div>",
            '<div class="unified-panel-body" id="list_repositories">',
            '<div id="standard-search" style="height: 2em; margin: 1em;">',
            '<span class="ui-widget" >',
            '<input class="search-box-input" id="search_box" name="search" data-shedurl="<%= tool_shed.replace(/%2f/g, "/") %>" placeholder="Search repositories by name or id" size="60" type="text" />',
            "</span>",
            "</div>",
            "<% if (category.get('repository_count') > 25) { %>",
            '<%= page_navigation %>',
            "<% } %>",
            '<div style="clear: both; margin-top: 1em;">',
            '<table class="grid table-striped">',
            '<thead id="grid-table-header">',
            "<tr>",
            '<th style="width: 10%;"><a class="fa fa-fw <%= sorting.class.owner %>" data-direction="<%= sorting.direction.owner %>" data-field="owner">Owner</a></th>',
            '<th style="width: 15%;"><a class="fa fa-fw <%= sorting.class.name %>" data-direction="<%= sorting.direction.name %>" data-field="name">Name</a></th>',
            '<th><a class="fa fa-fw <%= sorting.class.description %>" data-direction="<%= sorting.direction.description %>" data-field="description">Synopsis</a></th>',
            '<th style="width: 10%;">Type</th>',
            "</tr>",
            "</thead>",
            '<% _.each(category.get("repositories"), function(repository) { %>',
            "<tr>",
            "<td><%= repository.owner %></td>",
            "<td>",
            '<div style="float: left; margin-left: 1px;" class="menubutton split">',
            '<a href="#/repository/s/<%= tool_shed %>/r/<%= repository.id %>"><%= repository.name %></a>',
            "</div>",
            "</td>",
            "<td><%= repository.description %></td>",
            "<td><%= repository.type %></td>",
            "</tr>",
            "<% }); %>",
            "</table>",
            "</div>",
            "</div>"
        ].join("")
    )
});

export default {
    Category: ToolShedCategoryContentsView
};
