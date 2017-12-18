define([],
function() {

// toolshed group row view
var GroupListRowView = Backbone.View.extend({
    events: {},

    initialize : function( options ){
        this.render( options.group );
    },

    render: function( group ){
        var tmpl = this.templateRow();
        this.setElement(tmpl( { group:group } ));
        this.$el.show();
        return this;
    },

    templateRow: function() {
        return _.template([
                '<tr class="" data-id="<%- group.get("id") %>">',
                '<td><a href="groups#/<%= group.get("id") %>"><%= _.escape(group.get("name")) %></a></td>',
                // '<td>description</td>',
                '<td><%= group.get("total_members") %></td>',
                '<td><%= group.get("total_repos") %></td>',
                '</tr>'
        ].join(''));
  }
   
});

return {
    GroupListRowView: GroupListRowView
};

});
