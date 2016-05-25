define([],function(){var a=Backbone.Model.extend({urlRoot:Galaxy.root+"api/admin/repos"}),b=Backbone.Collection.extend({url:Galaxy.root+"api/admin/repos",model:a,dateComparator:function(a,b){var c=new Date(a.get("create_time").date),d=new Date(b.get("create_time").date);return c>d?-1:d>c?1:0},nameComparator:function(a,b){var c=a.get("name").toLowerCase(),d=b.get("name").toLowerCase();return c>d?-1:d>c?1:0},statusComparator:function(a,b){var c=a.get("status").toLowerCase(),d=b.get("status").toLowerCase(),e=["error","installing","cloning","setting tool versions","installing repository dependencies","installing tool dependencies","loading proprietary datatypes","new","installed","deactivated","uninstalled"];return e.indexOf(c)>e.indexOf(d)?-1:e.indexOf(c)<e.indexOf(d)?1:0},switchComparator:function(a){switch(a){case"date":this.comparator=this.dateComparator;break;case"name":this.comparator=this.nameComparator;break;case"owner":this.comparator="owner";break;case"installation":this.comparator=this.statusComparator;break;case"version":this.comparator="update"}}});return{Repo:a,Repos:b}});
//# sourceMappingURL=../../maps/admin/repos-model.js.map