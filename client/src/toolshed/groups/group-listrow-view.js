import _ from "underscore";
import Backbone from "backbone";

// toolshed group row view
const GroupListRowView = Backbone.View.extend({
    events: {},

    initialize: function (options) {
        this.render(options.group);
    },

    render: function (group) {
        const tmpl = this.templateRow();
        this.setElement(tmpl({ group: group }));
        this.$el.show();
        return this;
    },

    templateRow: function () {
        return _.template(
            [
                '<tr class="" data-id="<%- group.get("id") %>">',
                '<td><a href="groups#/<%= group.get("id") %>"><%= _.escape(group.get("name")) %></a></td>',
                // '<td>description</td>',
                '<td><%= group.get("total_members") %></td>',
                '<td><%= group.get("total_repos") %></td>',
                "</tr>",
            ].join("")
        );
    },
});

export default {
    GroupListRowView: GroupListRowView,
};
