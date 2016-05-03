define([
  "libs/toastr",
  "admin/repos-list-view"
  ],
  function(
    mod_toastr,
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
    ""         : "repos",
    "repos"    : "repos",
    "all"      : "all",
    "packages" : "packages",
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

  initialize: function(){
    Galaxy.adminapp = this;
    this.admin_router = new AdminRouter();

    this.admin_router.on( 'route:repos', function() {
      if (Galaxy.adminapp.adminReposListView){
        console.log('entering with tools')
        Galaxy.adminapp.adminReposListView.repaint({filter: 'with_tools'});
      } else{
        Galaxy.adminapp.adminReposListView = new mod_repos_list_view.AdminReposListView();
      }
    });

    this.admin_router.on( 'route:packages', function() {
      if (Galaxy.adminapp.adminReposListView){
        Galaxy.adminapp.adminReposListView.repaint({filter: 'packages'});
      } else{
        Galaxy.adminapp.adminReposListView = new mod_repos_list_view.AdminReposListView({filter: 'packages'});
      }
    });

    this.admin_router.on( 'route:all', function() {
      if (Galaxy.adminapp.adminReposListView){
        console.log('entering all')
        Galaxy.adminapp.adminReposListView.repaint({filter: 'all'});
      } else{
        Galaxy.adminapp.adminReposListView = new mod_repos_list_view.AdminReposListView({filter: 'all'});
      }
    });

    Backbone.history.start({pushState: false});
  }


});

return {
    GalaxyApp: GalaxyAdminApp
};

});
