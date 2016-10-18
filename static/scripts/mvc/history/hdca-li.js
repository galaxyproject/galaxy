define(["mvc/dataset/states","mvc/collection/collection-li","mvc/collection/collection-view","mvc/base-mvc","utils/localization"],function(a,b,c,d,e){"use strict";var f=b.DCListItemView,g=f.extend({className:f.prototype.className+" history-content",_setUpListeners:function(){f.prototype._setUpListeners.call(this),this.listenTo(this.model,{"change:populated change:visible":function(a,b){this.render()}})},_getFoldoutPanelClass:function(){switch(this.model.get("collection_type")){case"list":return c.ListCollectionView;case"paired":return c.PairCollectionView;case"list:paired":return c.ListOfPairsCollectionView;case"list:list":return c.ListOfListsCollectionView}throw new TypeError("Uknown collection_type: "+this.model.get("collection_type"))},_swapNewRender:function(b){f.prototype._swapNewRender.call(this,b);var c=this.model.get("populated")?a.OK:a.RUNNING;return this.$el.addClass("state-"+c),this.$el},toString:function(){var a=this.model?this.model+"":"(no model)";return"HDCAListItemView("+a+")"}});return g.prototype.templates=function(){var a=_.extend({},f.prototype.templates.warnings,{hidden:d.wrapTemplate(["<% if( !collection.visible ){ %>",'<div class="hidden-msg warningmessagesmall">',e("This collection has been hidden"),"</div>","<% } %>"],"collection")}),b=d.wrapTemplate(['<div class="title-bar clear" tabindex="0">','<span class="state-icon"></span>','<div class="title">','<span class="hid"><%- collection.hid %></span> ','<span class="name"><%- collection.name %></span>',"</div>",'<div class="subtitle"></div>',"</div>"],"collection");return _.extend({},f.prototype.templates,{warnings:a,titleBar:b})}(),{HDCAListItemView:g}});
//# sourceMappingURL=../../../maps/mvc/history/hdca-li.js.map