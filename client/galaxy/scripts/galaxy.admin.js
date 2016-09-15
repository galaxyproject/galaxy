define([
  "libs/toastr",
  "admin/repos-detail-view",
  "admin/repos-list-view"
  ],
  function(
    mod_toastr,
    mod_repos_detail_view,
    mod_repos_list_view
   ) {

var AdminRouter = Backbone.Router.extend({

  initialize: function() {
    this.routesHit = 0;
    // keep count of number of routes handled by the application
    Backbone.history.on( 'route', function() { this.routesHit++; }, this );

    this.bind( 'route', this.trackPageview );
  },

  routes: {
    ""                           : "repolist",
    "repos"                      : "repolist",
    "repos/v/:view"              : "repolist",
    "repos/v/:view/f/:filter"    : "repolist",
    "repos/:id"                  : "repodetail",
    // "repos(?view=:view)&(filter=:filter)"    : "repolist",

  },

  /**
   * If more than one route has been hit the user did not land on current
   * page directly so we can go back safely. Otherwise go to the home page.
   * Use replaceState if available so the navigation doesn't create an
   * extra history entry
   */
  back: function() {
    if( this.routesHit > 1 ) {
      window.history.back();
    } else {
      this.navigate( '#', { trigger:true, replace:true } );
    }
  }

});

var GalaxyAdminApp = Backbone.View.extend({

  app_config: {
    known_views: ['all', 'tools', 'packages', 'uninstalled']
  },

  initialize: function(){
    Galaxy.adminapp = this;
    this.admin_router = new AdminRouter();

    this.admin_router.on('route:repolist', function(view, filter) {
      if (Galaxy.adminapp.app_config.known_views.indexOf(view) === -1){
        view = 'all';
      }
      console.log('view: '+view+' section_filter: '+filter);
      if (Galaxy.adminapp.adminReposListView){
        console.log('recycling reposlist view');
        Galaxy.adminapp.adminReposListView.repaint({view: view, section_filter: filter});
      } else{
        console.log('new reposlist view');
        Galaxy.adminapp.adminReposListView = new mod_repos_list_view.AdminReposListView({view: view, section_filter: filter});
      }
    });
    this.admin_router.on('route:repodetail', function(id) {
      console.log('detail id:'+id);
      Galaxy.adminapp.adminRepoDetailView = new mod_repos_detail_view.AdminReposDetailView({id: id});
    });

    Backbone.history.start({pushState: false});
  }


});

return {
    GalaxyApp: GalaxyAdminApp
};

});
