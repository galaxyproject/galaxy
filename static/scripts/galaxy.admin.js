define(["libs/toastr","admin/repos-list-view"],function(a,b){var c=Backbone.Router.extend({initialize:function(){this.routesHit=0,Backbone.history.on("route",function(){this.routesHit++},this),this.bind("route",this.trackPageview)},routes:{"":"repolist",repos:"repolist","repos/v/:view":"repolist","repos/v/:view/f/:filter":"repolist","repos/:id":"repodetail"},back:function(){this.routesHit>1?window.history.back():this.navigate("#",{trigger:!0,replace:!0})}}),d=Backbone.View.extend({initialize:function(){Galaxy.adminapp=this,this.admin_router=new c,this.admin_router.on("route:repolist",function(a,c){console.log("view:"+a),console.log("filter:"+c),Galaxy.adminapp.adminReposListView?Galaxy.adminapp.adminReposListView.repaint({view:a,filter:c}):Galaxy.adminapp.adminReposListView=new b.AdminReposListView({view:a,filter:c})}),this.admin_router.on("route:repodetail",function(a){console.log("detail id:"+a)}),Backbone.history.start({pushState:!1})}});return{GalaxyApp:d}});
//# sourceMappingURL=../maps/galaxy.admin.js.map