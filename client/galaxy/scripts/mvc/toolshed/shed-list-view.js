import Backbone from "backbone";
import _ from "underscore";
import _l from "utils/localization";
import toolshed_model from "mvc/toolshed/toolshed-model";
import toolshed_util from "mvc/toolshed/util";

var ShedListView = Backbone.View.extend({
    initialize: function(options) {
        this.options = _.defaults(this.options || {}, this.defaults);
        this.model = new toolshed_model.ShedsCollection();
        this.listenTo(this.model, "sync", this.render);
        this.model.fetch();
    },

    el: "#center",

    render: function(options) {
        this.options = _.defaults(this.options || {}, options, this.defaults);
        var toolshed_list_template = this.templateToolshedList();
        this.$el.html(
            toolshed_list_template({
                title: _l("Configured Galaxy Tool Sheds"),
                tool_sheds: this.model.models,
                queue: toolshed_util.queueLength()
            })
        );
        $("#center").css("overflow", "auto");
    },

    templateToolshedList: function() {
        return _.template(
            `<div class='shed-style-container'>
                <div class='header'>
                <h2>
                ${_l("Configured Tool Sheds")}
                </h2>
                <span><a href='#/queue'>Repository Queue (<%= queue %>)</a></span>
                <div style='clear:both;'></div>
                </div'>
                <% _.each(tool_sheds, function(shed) { %>
                    <div>
                    <a href='#/categories/s/<%= shed.get('url') %>'><%= shed.get('name') %></a>
                    </div>
                <% }); %>
                </div>`
        );
    }
});

export default {
    ShedListView: ShedListView
};
