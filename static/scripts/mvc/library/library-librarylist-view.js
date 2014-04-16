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

    // initialize
    initialize : function(options){
        this.options = _.defaults(this.options || {}, options);
        var viewContext = this;

        this.rowViews = {};

        this.collection = new mod_library_model.Libraries();

        this.collection.fetch({
          success: function(libraries){
            viewContext.render();
          },
          error: function(model, response){
            mod_toastr.error('An error occured. Please try again.');
          }
        });
    },

    /** Renders the libraries table either from the object's own collection, 
     or from a given array of library models,
     or renders an empty list in case no data is given. */
    render: function (options) {
        var template = this.templateLibraryList();
        var libraries_to_render = null;
        var include_deleted = Galaxy.libraries.preferences.get('with_deleted');
        var models = null;
        if (typeof options !== 'undefined'){
            include_deleted = typeof options.with_deleted !== 'undefined' ? options.with_deleted : false;
            models = typeof options.models !== 'undefined' ? options.models : null;
        }

        if (this.collection !== null && models === null){
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
        // modification of upper DOM element to show scrollbars due to the #center element inheritance
        $("#center").css('overflow','auto');
    },

    renderRows: function(libraries_to_render){
        for (var i = 0; i < libraries_to_render.length; i++) {
          var library = libraries_to_render[i];
          var cachedView = _.findWhere(this.rowViews, {id: library.get('id')});
          if (cachedView !== undefined && this instanceof Backbone.View){
            cachedView.delegateEvents();
            this.$el.find('#library_list_body').append(cachedView.el);
          } else {
            var rowView = new mod_library_libraryrow_view.LibraryRowView(library);
            this.$el.find('#library_list_body').append(rowView.el);
            // save new rowView to cache
            this.rowViews[library.get('id')] = rowView;
          }
        }
    },

    sort_clicked : function(){
        if (Galaxy.libraries.preferences.get('sort_order') === 'asc'){
            this.sortLibraries('name','desc');
            Galaxy.libraries.preferences.set({'sort_order': 'desc'});
        } else {
            this.sortLibraries('name','asc');
            Galaxy.libraries.preferences.set({'sort_order': 'asc'});
        }
        this.render();
    },

    /** Sorts the underlying collection according to the parameters received. 
        Currently supports only sorting by name. */
    sortLibraries: function(sort_by, order){
        if (sort_by === 'name'){
            if (order === 'asc'){
                this.collection.sortByNameAsc();
            } else if (order === 'desc'){
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
        tmpl_array.push('<div>There are no libraries visible to you. If you expected some to show up please consult the <a href="https://wiki.galaxyproject.org/Admin/DataLibraries/LibrarySecurity">library security wikipage</a>.</div>');
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
    
    templateNewLibraryInModal: function(){
        tmpl_array = [];

        tmpl_array.push('<div id="new_library_modal">');
        tmpl_array.push('   <form>');
        tmpl_array.push('       <input type="text" name="Name" value="" placeholder="Name">');
        tmpl_array.push('       <input type="text" name="Description" value="" placeholder="Description">');
        tmpl_array.push('       <input type="text" name="Synopsis" value="" placeholder="Synopsis">');
        tmpl_array.push('   </form>');
        tmpl_array.push('</div>');

        return tmpl_array.join('');
    },

    redirectToHome: function(){
        window.location = '../';
    },
    redirectToLogin: function(){
        window.location = '/user/login';
    },

    // show/hide create library modal
    show_library_modal : function (event){
        event.preventDefault();
        event.stopPropagation();

        // create modal
        var self = this;
        this.modal = Galaxy.modal;
        this.modal.show({
            closing_events  : true,
            title           : 'Create New Library',
            body            : this.templateNewLibraryInModal(),
            buttons         : {
                'Create'    : function() {self.create_new_library_event();},
                'Close'     : function() {self.modal.hide();}
            }
        });
    },

    // create the new library from modal
    create_new_library_event: function(){
        var libraryDetails = this.serialize_new_library();
        if (this.validate_new_library(libraryDetails)){
            var library = new mod_library_model.Library();
            var self = this;
            library.save(libraryDetails, {
              success: function (library) {
                self.collection.add(library);
                self.modal.hide();
                self.clear_library_modal();
                self.render();
                mod_toastr.success('Library created');
              },
              error: function(){
                mod_toastr.error('An error occured :(');
              }
            });
        } else {
            mod_toastr.error('Library\'s name is missing');
        }
        return false;
    },

    // clear the library modal once saved
    clear_library_modal : function(){
        $("input[name='Name']").val('');
        $("input[name='Description']").val('');
        $("input[name='Synopsis']").val('');
    },

    // serialize data from the form
    serialize_new_library : function(){
        return {
            name: $("input[name='Name']").val(),
            description: $("input[name='Description']").val(),
            synopsis: $("input[name='Synopsis']").val()
        };
    },

    // validate new library info
    validate_new_library: function(libraryDetails){
        return libraryDetails.name !== '';
    }
});

return {
    LibraryListView: LibraryListView
};

});
