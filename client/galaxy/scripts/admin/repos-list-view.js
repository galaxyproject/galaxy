define([
  "libs/toastr",
  "admin/repos-row-view",
  "admin/repos-model",
  ],
  function(
    mod_toastr,
    mod_repo_row_view,
    mod_repos_model
   ) {

var AdminReposListView = Backbone.View.extend({
  el: '#center',
  rowViews: {},
  defaults: {
    filter: 'with_tools'
  },

  initialize: function( options ){
    this.options = _.defaults( this.options || {}, options, this.defaults );
    this.collection = new mod_repos_model.Repos();
    // start to listen if someone modifies the collection
    this.listenTo( this.collection, 'add', this.renderOne );
    // this.listenTo( this.collection, 'change', this.renderOne );
    // this.listenTo( this.collection, 'reset', this.renderAll );
    // this.listenTo( this.collection, 'sync', this.renderAll );
    // this.listenTo( this.collection, 'remove', this.removeOne );
    this.render();
    this.fetchRepos();
    this.repaint();
  },

  render: function(options){
    this.options = _.extend( this.options, options );
    var repo_list_template = this.templateRepoList();
    this.$el.html(repo_list_template());
    $( "#center" ).css( 'overflow','auto' );
  },

  fetchRepos: function(){
    this.collection.fetch({
      success: function(collection, response, options){

      },
      error: function(collection, response, options){

      }
    });
  },

  repaint: function(options){
    this.options = _.extend( this.options, options );
    this.removeAllRows();
    this.adjustMenu();
    this.renderAll();
  },

  adjustMenu: function(options){
    this.options = _.extend( this.options, options );
    this.$el.find('li').removeClass('active');
    $('.tab_' + this.options.filter).addClass('active');
    var that = this;
    // _.filter(this.collection, function(repo){ return repo.type === that.options.filter; });
    // this.updateRepoCounts();
  },

  updateRepoCounts: function(options){
    this.options = _.extend( this.options, options );
    // this.$el.find('.tab_with_tools > a').text('With Tools (125)');

  },

  /**
   * Iterates this view's collection and calls the render
   * function for each in case it passes the filter.
   */
  renderAll: function(options){
    this.options = _.extend( this.options, options );
    var that = this;
    _.each( this.collection.models.reverse(), function( repo ) {
      if (that.options.filter === repo.get('type')){
        that.renderOne( repo );
      }
    });
  },

  /**
   * Creates a view for the given repo and adds it to the list view.
   * @param {Repo} model of the view that will be rendered
   */
  renderOne: function(repo){
      var repoView = new mod_repo_row_view.AdminReposRowView({repo: repo});
      this.rowViews[repo.get('id')] = repoView;
      this.$el.find('#repos_list_body').append(repoView.el);
  },

  removeOne: function(){

  },

  /**
   * Remove all dataset and folder row elements from the DOM.
   */
  removeAllRows: function(){
    $('.repo-row').remove();
  },

  templateRepoList: function(){
    return _.template([
      '<div class="library_style_container">',
        '<div id="toolbar_form">',
          '<div id="repositories_toolbar">',
            '<form class="form-inline" role="form">',
              '<span><strong>REPOSITORIES</strong></span>',
              // '<div class="form-group toolbar-item">',
              //   '<input type="text" class="form-control repositories-search-input" placeholder="Search" size="30">',
              // '</div>',
              // '<span class="help-button" data-toggle="tooltip" data-placement="top" title="Visit Wiki">',
              //   '<a href="LINK TO DOCS" target="_blank">',
              //     '<button class="primary-button" type="button"><span class="fa fa-question-circle"></span> Help</button>',
              //   '</a>',
              // '</span>',
            '</form>',
            '<ul class="nav nav-tabs">',
              '<li role="presentation" class="tab_with_tools"><a href="#repos">With Tools</a></li>',
              '<li role="presentation" class="tab_tool_dependencies"><a href="#packages">Packages</a></li>',
              '<li role="presentation" class="tab_suites"><a href="#packages">Suites</a></li>',
              '<li role="presentation" class="tab_with_dm"><a href="#packages">Data Managers</a></li>',
              '<li role="presentation" class="tab_with_datatypes"><a href="#packages">Datatypes</a></li>',
            '</ul>',
          '</div>',
        '</div>',
        '<div id="repositories_list">',
          '<div class="repos_container table-responsive">',
            '<table class="grid table table-condensed">',
              '<thead>',
                '<th>',
                  '<a class="sort-repos-link" title="Click to reverse order" href="#">',
                    'Name',
                  '</a>',
                '</th>',
                '<th>Owner</th>',
                '<th>Installation</th> ',
                '<th>Category</th>',
                '<th>Version</th>',
                '<th>Date Installed</th>',
              '</thead>',
              '<tbody id="repos_list_body">',
              // repo item views will attach here
              '</tbody>',
            '</table>',
          '</div>',
        '</div>',
      '</div>'
    ].join(''));
  }

});

return {
    AdminReposListView: AdminReposListView
};

});
