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
    ""                    : "repolist",
    "repos?view=:view"    : "repolist",
    // "repos/:id"           : "repos",

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

    this.admin_router.on('route:repolist', function(view) {
      var show_view = 'all'
      if (typeof view !== 'undefined') {
        show_view = view;
      }
      if (Galaxy.adminapp.adminReposListView){
        Galaxy.adminapp.adminReposListView.repaint({filter: show_view});
      } else{
        Galaxy.adminapp.adminReposListView = new mod_repos_list_view.AdminReposListView({filter: show_view});
      }
    });

    Backbone.history.start({pushState: false});
  }


});

return {
    GalaxyApp: GalaxyAdminApp
};

});
