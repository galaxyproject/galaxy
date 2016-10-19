define(["mvc/list/list-item","mvc/dataset/dataset-li","mvc/base-mvc","utils/localization"],function(a,b,c,d){"use strict";var e=a.FoldoutListItemView,f=a.ListItemView,g=e.extend({className:e.prototype.className+" dataset-collection",id:function(){return["dataset_collection",this.model.get("id")].join("-")},initialize:function(a){this.linkTarget=a.linkTarget||"_blank",this.hasUser=a.hasUser,e.prototype.initialize.call(this,a)},_setUpListeners:function(){e.prototype._setUpListeners.call(this),this.listenTo(this.model,"change",function(a,b){_.has(a.changed,"deleted")?this.render():_.has(a.changed,"element_count")&&this.$("> .title-bar .subtitle").replaceWith(this._renderSubtitle())})},_renderSubtitle:function(){return $(this.templates.subtitle(this.model.toJSON(),this))},_getFoldoutPanelOptions:function(){var a=e.prototype._getFoldoutPanelOptions.call(this);return _.extend(a,{linkTarget:this.linkTarget,hasUser:this.hasUser})},$selector:function(){return this.$("> .selector")},toString:function(){var a=this.model?this.model+"":"(no model)";return"DCListItemView("+a+")"}});g.prototype.templates=function(){var a=_.extend({},e.prototype.templates.warnings,{error:c.wrapTemplate(["<% if( model.error ){ %>",'<div class="errormessagesmall">',d("There was an error getting the data for this collection"),": <%- model.error %>","</div>","<% } %>"]),purged:c.wrapTemplate(["<% if( model.purged ){ %>",'<div class="purged-msg warningmessagesmall">',d("This collection has been deleted and removed from disk"),"</div>","<% } %>"]),deleted:c.wrapTemplate(["<% if( model.deleted && !model.purged ){ %>",'<div class="deleted-msg warningmessagesmall">',d("This collection has been deleted"),"</div>","<% } %>"])}),b=c.wrapTemplate(['<div class="title-bar clear" tabindex="0">','<div class="title">','<span class="name"><%- collection.element_identifier || collection.name %></span>',"</div>",'<div class="subtitle"></div>',"</div>"],"collection"),f=c.wrapTemplate(['<div class="subtitle">','<% var countText = collection.element_count? ( collection.element_count + " " ) : ""; %>','<%        if( collection.collection_type === "list" ){ %>',d("a list of <%- countText %>datasets"),'<% } else if( collection.collection_type === "paired" ){ %>',d("a pair of datasets"),'<% } else if( collection.collection_type === "list:paired" ){ %>',d("a list of <%- countText %>dataset pairs"),'<% } else if( collection.collection_type === "list:list" ){ %>',d("a list of <%- countText %>dataset lists"),"<% } %>","</div>"],"collection");return _.extend({},e.prototype.templates,{warnings:a,titleBar:b,subtitle:f})}();var h=f.extend({className:f.prototype.className+" dataset-collection-element",initialize:function(a){a.logger&&(this.logger=this.model.logger=a.logger),this.log("DCEListItemView.initialize:",a),f.prototype.initialize.call(this,a)},toString:function(){var a=this.model?this.model+"":"(no model)";return"DCEListItemView("+a+")"}});h.prototype.templates=function(){var a=c.wrapTemplate(['<div class="title-bar clear" tabindex="0">','<div class="title">','<span class="name"><%- element.element_identifier %></span>',"</div>",'<div class="subtitle"></div>',"</div>"],"element");return _.extend({},f.prototype.templates,{titleBar:a})}();var i=b.DatasetListItemView.extend({className:b.DatasetListItemView.prototype.className+" dataset-collection-element",initialize:function(a){a.logger&&(this.logger=this.model.logger=a.logger),this.log("DatasetDCEListItemView.initialize:",a),b.DatasetListItemView.prototype.initialize.call(this,a)},_fetchModelDetails:function(){var a=this;return a.model.inReadyState()&&!a.model.hasDetails()?a.model.fetch({silent:!0}):jQuery.when()},toString:function(){var a=this.model?this.model+"":"(no model)";return"DatasetDCEListItemView("+a+")"}});i.prototype.templates=function(){var a=c.wrapTemplate(['<div class="title-bar clear" tabindex="0">','<span class="state-icon"></span>','<div class="title">','<span class="name"><%- element.element_identifier %></span>',"</div>","</div>"],"element");return _.extend({},b.DatasetListItemView.prototype.templates,{titleBar:a})}();var j=g.extend({className:g.prototype.className+" dataset-collection-element",_swapNewRender:function(a){g.prototype._swapNewRender.call(this,a);var b=this.model.get("state")||"ok";return this.$el.addClass("state-"+b),this.$el},toString:function(){var a=this.model?this.model+"":"(no model)";return"NestedDCDCEListItemView("+a+")"}});return{DCListItemView:g,DCEListItemView:h,DatasetDCEListItemView:i,NestedDCDCEListItemView:j}});
//# sourceMappingURL=../../../maps/mvc/collection/collection-li.js.map