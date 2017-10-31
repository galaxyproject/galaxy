define([ "mvc/toolshed/toolshed-model" ], function(toolshed_model) {
    var View = Backbone.View.extend({
        defaults: {
            tool_sheds: [ {
                url: "https://toolshed.g2.bx.psu.edu/",
                name: "Galaxy Main Tool Shed"
            } ]
        },
        initialize: function() {
            console.log("init");
            this.model = new toolshed_model.ShedsCollection(), this.listenTo(this.model, "sync", this.render), 
            this.model.fetch();
        },
        el: "#center",
        render: function(options) {
            this.options = _.defaults(this.options || {}, options, this.defaults);
            var toolshed_list_template = this.templateToolshedList;
            this.$el.html(toolshed_list_template({
                tool_sheds: this.model.models
            }));
        },
        templateToolshedList: _.template([ '<div class="tab-pane" id="list_toolsheds">', '<div class="toolFormTitle">Accessible Galaxy tool sheds</div>', '<div class="toolFormBody">', '<div class="form-row">', '<table class="grid">', "<% _.each(tool_sheds, function(shed) { %>", '<tr class="libraryTitle">', "<td>", '<div style="float: left; margin-left: 1px;" class="menubutton split">', '<a class="view-info shed-selector" href="#/categories/s/<%= shed.get("url") %>"><%= shed.get("name") %></a>', "</div>", "</td>", "</tr>", "<% }); %>", "</table>", "</div>", '<div style="clear: both"></div>', "</div>", "</div>" ].join(""))
    });
    return {
        ShedListView: View
    };
});