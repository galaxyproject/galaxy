define([
    "galaxy.masthead",
    "mvc/base-mvc",
    "utils/utils",
    "libs/toastr",
    "mvc/library/library-model",
    "mvc/library/library-libraryrow-view"],
function(mod_masthead,
         mod_baseMVC,
         mod_utils,
         mod_toastr,
         mod_library_model,
         mod_library_libraryrow_view) {

var LibraryListView = Backbone.View.extend({
    el: '#libraries_element',

    events: {
        'click .sort-libraries-link'    : 'sort_clicked'
    },

    modal: null,

    // collection of {Item}s
    collection: null,

    // map of library model ids to library views = cache
    rowViews: {},

    initialize : function(options){
        this.options = _.defaults(this.options || {}, options);
        var that = this;
        this.rowViews = {};
        this.collection = new mod_library_model.Libraries();
        this.collection.fetch({
          success: function(){
            that.render();
          },
          error: function(model, response){
              if (typeof response.responseJSON !== "undefined"){
                mod_toastr.error(response.responseJSON.err_msg);
              } else {
                mod_toastr.error('An error ocurred.');
              }
          }
        });
    },

    /** Renders the libraries table either from the object's own collection, 
     *  or from a given array of library models,
     *  or renders an empty list in case no data is given. */
    render: function (options) {
        $(".tooltip").hide();
        var template = this.templateLibraryList();
        var libraries_to_render = null;
        var include_deleted = Galaxy.libraries.preferences.get('with_deleted');
        var models = null;
        if (typeof options !== 'undefined'){
            include_deleted = typeof options.with_deleted !== 'undefined' ? options.with_deleted : false;
            models = typeof options.models !== 'undefined' ? options.models : null;
        }

        if (this.collection !== null && models === null){
            this.sortLibraries();
            if (include_deleted){ // show all the libraries
              libraries_to_render = this.collection.models;
            } else{ // show only undeleted libraries
              libraries_to_render = this.collection.where({deleted: false});
            }
        } else if (models !== null){
            libraries_to_render = models;
        } else {
            libraries_to_render = [];
            }

        this.$el.html(template({length: libraries_to_render.length, order: Galaxy.libraries.preferences.get('sort_order') }));

        if (libraries_to_render.length > 0){
            this.renderRows(libraries_to_render);
        }
        // initialize the library tooltips
        $("#center [data-toggle]").tooltip();
        // modification of upper DOM element to show scrollbars due 
        // to the #center element inheritance
        $("#center").css('overflow','auto');
    },

    /** Renders all given models as rows in the library list */
    renderRows: function(libraries_to_render){
        for (var i = 0; i < libraries_to_render.length; i++) {
          var library = libraries_to_render[i];
          var cachedView = _.findWhere(this.rowViews, {id: library.get('id')});
          if (cachedView !== undefined && this instanceof Backbone.View){
            cachedView.delegateEvents();
            this.$el.find('#library_list_body').append(cachedView.el);
          } else {
            this.renderOne({library:library})
          }
        }
    },

    /**
     * Creates a view for the given model and adds it to the libraries view.
     * @param {Library} model of the view that will be rendered
     */
    renderOne: function(options){
        var library = options.library;
        var rowView = new mod_library_libraryrow_view.LibraryRowView(library);
        // we want to prepend new item
        if (options.prepend){ 
            this.$el.find('#library_list_body').prepend(rowView.el);
        } else {
            this.$el.find('#library_list_body').append(rowView.el);
        }
        // save new rowView to cache
        this.rowViews[library.get('id')] = rowView;
    },

    /** Table heading was clicked, update sorting preferences and re-render */
    sort_clicked : function(){
        if (Galaxy.libraries.preferences.get('sort_order') === 'asc'){
            Galaxy.libraries.preferences.set({'sort_order': 'desc'});
        } else {
            Galaxy.libraries.preferences.set({'sort_order': 'asc'});
        }
        this.render();
    },

    /** Sorts the underlying collection according to the parameters received. 
        Currently supports only sorting by name. */
    sortLibraries: function(){
        if (Galaxy.libraries.preferences.get('sort_by') === 'name'){
            if (Galaxy.libraries.preferences.get('sort_order') === 'asc'){
                this.collection.sortByNameAsc();
            } else if (Galaxy.libraries.preferences.get('sort_order') === 'desc'){
                this.collection.sortByNameDesc();
            }
        }
    },

// MMMMMMMMMMMMMMMMMM
// === TEMPLATES ====
// MMMMMMMMMMMMMMMMMM

    templateLibraryList: function(){
        tmpl_array = [];

        tmpl_array.push('<div class="library_container table-responsive">');
        tmpl_array.push('<% if(length === 0) { %>');
        tmpl_array.push('<div>There are no libraries visible to you. If you expected some to show up please consult the <a href="https://wiki.galaxyproject.org/Admin/DataLibraries/LibrarySecurity">library security wikipage</a> or visit the <a href="https://biostar.usegalaxy.org/">Galaxy support site</a>.</div>');
        tmpl_array.push('<% } else{ %>');
        tmpl_array.push('<table class="grid table table-condensed">');
        tmpl_array.push('   <thead>');
        tmpl_array.push('     <th style="width:30%;"><a class="sort-libraries-link" title="Click to reverse order" href="#">name</a> <span title="Sorted alphabetically" class="fa fa-sort-alpha-<%- order %>"></span></th>');
        tmpl_array.push('     <th style="width:22%;">description</th>');
        tmpl_array.push('     <th style="width:22%;">synopsis</th> ');
        tmpl_array.push('     <th style="width:26%;"></th> ');
        tmpl_array.push('   </thead>');
        tmpl_array.push('   <tbody id="library_list_body">');
        // library item views will attach here
        tmpl_array.push('   </tbody>');
        tmpl_array.push('</table>');
        tmpl_array.push('<% }%>');
        tmpl_array.push('</div>');

        return _.template(tmpl_array.join(''));
    },


    redirectToHome: function(){
        window.location = '../';
    },
    redirectToLogin: function(){
        window.location = '/user/login';
    },

});

return {
    LibraryListView: LibraryListView
};

});
