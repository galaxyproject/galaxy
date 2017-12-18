define('toolshed/groups/group-listrow-view', ['exports'], function(exports) {
    'use strict';

    Object.defineProperty(exports, "__esModule", {
        value: true
    });
    // toolshed group row view
    var GroupListRowView = Backbone.View.extend({
        events: {},

        initialize: function initialize(options) {
            this.render(options.group);
        },

        render: function render(group) {
            var tmpl = this.templateRow();
            this.setElement(tmpl({
                group: group
            }));
            this.$el.show();
            return this;
        },

        templateRow: function templateRow() {
            return _.template(['<tr class="" data-id="<%- group.get("id") %>">', '<td><a href="groups#/<%= group.get("id") %>"><%= _.escape(group.get("name")) %></a></td>',
                // '<td>description</td>',
                '<td><%= group.get("total_members") %></td>', '<td><%= group.get("total_repos") %></td>', "</tr>"
            ].join(""));
        }
    });

    exports.default = {
        GroupListRowView: GroupListRowView
    };
});
//# sourceMappingURL=../../../maps/toolshed/groups/group-listrow-view.js.map
