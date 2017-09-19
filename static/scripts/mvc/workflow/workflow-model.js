"use strict";define(["mvc/base-mvc"],function(o){var e=Backbone.Model.extend(o.LoggableMixin).extend({_logNamespace:"workflow",urlRoot:"/api/workflows",toJSON:function(){return{workflow:this.attributes}}});return{WorkflowItem:e,WorkflowCollection:Backbone.Collection.extend({model:e,url:"/api/workflows"})}});
//# sourceMappingURL=../../../maps/mvc/workflow/workflow-model.js.map
