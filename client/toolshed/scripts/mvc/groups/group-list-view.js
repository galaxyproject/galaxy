define([
    "libs/toastr",
    "toolshed/scripts/mvc/groups/group-model",
    "toolshed/scripts/mvc/groups/group-listrow-view"

], function(
    mod_toastr,
    mod_group_model,
    mod_group_row
){

var GroupListView = Backbone.View.extend({
    el: '#groups_element',
    defaults: {},

    /**
     * Initialize and fetch the groups from server. 
     * Async render afterwards.
     * @param  {object} options an object with options
     */
    initialize : function( options ){
        this.options = _.defaults( this.options || {}, this.defaults, options );
        var that = this;
        window.globalTS.groups.collection = new mod_group_model.Groups();
        window.globalTS.groups.collection.fetch({
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

    fetch: function(){
    },

    /** 
     * Render the groups table from the object's own collection. 
     */
    render: function ( options ) {
        this.options = _.extend( this.options, options );
        $( ".tooltip" ).hide();
        var template = this.templateGroupsList();
        this.$el.html( template( { length: window.globalTS.groups.collection.models.length } ) );
        this.renderRows( window.globalTS.groups.collection.models );
        $( "#center [data-toggle]" ).tooltip();
        $( "#center" ).css( 'overflow','auto' );
    },

    /** 
     * Render all given models as rows in the groups list
     * @param  {array} groups_to_render array of group models to render
     */
    renderRows: function( groups_to_render ){
        for ( var i = 0; i < groups_to_render.length; i++ ) {
            var group = groups_to_render[i];
            this.renderOne( { group: group } )
        }
    },

    /**
     * Create a view for the given model and add it to the groups view.
     * @param {Group} model of the view that will be rendered
     */
    renderOne: function( options ){
        var rowView = new mod_group_row.GroupListRowView( options );
        this.$el.find( '#group_list_body' ).append( rowView.el );
    },

    /**
     * Table heading was clicked, update sorting preferences and re-render.
     * @return {[type]} [description]
     */
    // sort_clicked : function(){
    //     if (Galaxy.libraries.preferences.get('sort_order') === 'asc'){
    //         Galaxy.libraries.preferences.set({'sort_order': 'desc'});
    //     } else {
    //         Galaxy.libraries.preferences.set({'sort_order': 'asc'});
    //     }
    //     this.render();
    // },

    /**
     * Sort the underlying collection according to the parameters received.
     * Currently supports only sorting by name. 
     */
    // sortLibraries: function(){
    //     if (Galaxy.libraries.preferences.get('sort_by') === 'name'){
    //         if (Galaxy.libraries.preferences.get('sort_order') === 'asc'){
    //             this.collection.sortByNameAsc();
    //         } else if (Galaxy.libraries.preferences.get('sort_order') === 'desc'){
    //             this.collection.sortByNameDesc();
    //         }
    //     }
    // },

    // redirectToHome: function(){
    //     window.location = '../';
    // },
    // redirectToLogin: function(){
    //     window.location = '/user/login';
    // },

// MMMMMMMMMMMMMMMMMM
// === TEMPLATES ====
// MMMMMMMMMMMMMMMMMM

    templateGroupsList: function(){
        tmpl_array = [];

        tmpl_array.push('<div id="groups">');
        tmpl_array.push('</div>');
        tmpl_array.push('<div class="groups_container table-responsive">');
        tmpl_array.push('<% if(length === 0) { %>');
        tmpl_array.push('<div>There are no groups yet.</div>');
        tmpl_array.push('<% } else{ %>');
        tmpl_array.push('<table class="grid table table-condensed">');
        tmpl_array.push('   <thead>');
        tmpl_array.push('     <th>Name</th>');
        // tmpl_array.push('     <th style="width:22%;">description</th>');
        tmpl_array.push('     <th>Members</th> ');
        tmpl_array.push('     <th>Repositories</th>');
        tmpl_array.push('   </thead>');
        tmpl_array.push('   <tbody id="group_list_body">');
        // group item views will attach here
        tmpl_array.push('   </tbody>');
        tmpl_array.push('</table>');
        tmpl_array.push('<% }%>');
        tmpl_array.push('</div>');

        return _.template(tmpl_array.join(''));
    },

});

return {
    GroupListView: GroupListView
};

});
