define([
    "libs/toastr",
    "toolshed/scripts/mvc/groups/group-model"
    ],
function(
    mod_toastr,
    mod_group_model
    ) {

// toolshed group detail view
var GroupDetailView = Backbone.View.extend({
    el: "#groups_element",
    options: {},
    app: null,

    initialize : function( options ){
        this.options = _.extend( this.options, options );
        this.app = window.globalTS.groups;

        if ( this.app.collection !== null ){
            this.model = this.app.collection.get( this.options.group_id );
            this.render();
        } else {
            this.fetchGroup();
        }

    },

    fetchGroup: function( options ){
        var that = this;
        this.options = _.extend( this.options, options );
        this.model = new mod_group_model.Group( { id: this.options.group_id } );
        this.model.fetch({
          success: function( model ){
            console.log( 'received data: ' );
            console.log( model );
            that.render();
          },
          error: function( model, response ){
              if ( typeof response.responseJSON !== "undefined" ){
                mod_toastr.error( response.responseJSON.err_msg );
              } else {
                mod_toastr.error( 'An error ocurred.' );
              }
          }
        });
    },

    render: function(){
        var template = this.templateRow();
        this.$el.html( template( { group: this.model } ) );
        $( "#center [data-toggle]" ).tooltip();
        $( "#center" ).css( 'overflow','auto' );
    },

    templateRow: function() {
        return _.template([
                '<div>',
                    '<h3><%= _.escape(group.get("name")) %></h3>',
                    '<p class="" style="color:gray;">',
                    'A group of <%= group.get("members").length %> members with <%= group.get("repositories").length %> repositories and a total of <%= group.get("total_downloads") %> combined repository clones.</p>',

                    '<h3>Members</h3>',
                    '<table class="grid table table-condensed">',
                        '<thead>',
                            '<th>Name</th>',
                            '<th>Repositories</th>',
                            '<th>Registered</th>',
                        '</thead>',
                        '<tbody>',
                            '<% _.each(group.get("members"), function(member) { %>',
                            '<tr>',
                                '<td>',
                                    '<%= _.escape(member.username) %>',
                                '</td>',
                                '<td>',
                                    '<a data-toggle="tooltip" data-placement="top" title="Repositories of <%= _.escape(member.username) %>" href="/repository/browse_repositories_by_user?user_id=<%= member.id %>&use_panels=true" id="<%= member.id %>"><%= member.user_repos_count %></a>',
                                '</td>',
                                '<td>',
                                    '<%= member.time_created %>',
                                '</td>',
                            '</tr>',
                            '<% }); %>',
                        '</tbody>',
                    '</table>',

                    '<h3>Repositories</h3>',
                    '<table class="grid table table-condensed">',
                        '<thead>',
                            '<th>Name</th>',
                            '<th>Description</th>',
                            '<th>Clones</th>',
                            '<th>Owner</th>',
                            '<th>Categories</th>',
                            '<th>Created</th>',
                            '<th>Updated</th>',
                            '<th>Rating</th>',
                            '<th>Verified</th>',
                        '</thead>',
                        '<tbody>',
                            '<% _.each(group.get("repositories"), function(repo) { %>',
                                '<tr>',
                                    '<td>',
                                        '<a data-toggle="tooltip" data-placement="top" title="Details of <%= _.escape(repo.name) %>" href="/view/<%= _.escape(repo.owner) %>/<%= _escape(repo.name) %>" id="<%= repo.id %>"><%= _.escape(repo.name) %></a>',
                                    '</td>',
                                    '<td>',
                                        '<%= _.escape(repo.description) %>',
                                    '</td>',
                                    '<td>',
                                        '<%= repo.times_downloaded %>',
                                    '</td>',
                                    '<td>',
                                        '<%= _.escape(repo.owner) %>',
                                    '</td>',
                                    '<td>',
                                        '<% _.each((repo.categories), function(cat) { %>',
                                            '<a data-toggle="tooltip" data-placement="top" title="Repositories in <%= cat.name %>" href="/repository/browse_repositories_in_category?id=<%= cat.id %>&use_panels=true"><%= cat.name %></a><br/>',
                                        // '<%= repo.categories %>',
                                        '<% }); %>',
                                    '</td>',
                                    '<td data-toggle="tooltip" data-placement="top" title="<%= repo.time_created_full %>">',
                                        '<%= repo.time_created %>',
                                    '</td>',
                                    '<td data-toggle="tooltip" data-placement="top" title="<%= repo.time_updated_full %>">',
                                        '<%= repo.time_updated %>',
                                    '</td>',
                                    '<td>',
                                        '<%= repo.ratings_mean %>',
                                    '</td>',
                                    '<td>',
                                        '<%= repo.approved %>',
                                    '</td>',
                                '</tr>',
                            '<% }); %>',
                        '</tbody>',
                    '</table>',
                '</div>'
        ].join(''));
  }
});
return {
    GroupDetailView: GroupDetailView
};

});

