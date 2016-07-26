define(["mvc/ui/ui-frames"],function(a){return Backbone.View.extend({initialize:function(b){var c=this;b=b||{},this.frames=new a.View({visible:!1}),this.setElement(this.frames.$el),this.buttonActive=b.collection.add({id:"enable-scratchbook",icon:"fa-th",tooltip:"Enable/Disable Scratchbook",onclick:function(){c.active=!c.active,c.buttonActive.set({toggle:c.active,show_note:c.active,note_cls:c.active&&"fa fa-check"}),!c.active&&c.frames.hide()},onbeforeunload:function(){if(c.frames.length()>0)return"You opened "+c.frames.length()+" frame(s) which will be lost."}}),this.buttonLoad=b.collection.add({id:"show-scratchbook",icon:"fa-eye",tooltip:"Show/Hide Scratchbook",show_note:!0,visible:!1,onclick:function(a){c.frames.visible?c.frames.hide():c.frames.show()}}),this.frames.on("add remove",function(){this.visible&&0==this.length()&&this.hide(),c.buttonLoad.set({note:this.length(),visible:this.length()>0})}).on("show hide ",function(){c.buttonLoad.set({toggle:this.visible,icon:this.visible&&"fa-eye"||"fa-eye-slash"})}),this.history_cache={}},addDataset:function(a){var b=this,c=null;if(Galaxy&&Galaxy.currHistoryPanel){var d=Galaxy.currHistoryPanel.collection.historyId;this.history_cache[d]={name:Galaxy.currHistoryPanel.model.get("name"),dataset_ids:[]},Galaxy.currHistoryPanel.collection.each(function(a){!a.get("deleted")&&a.get("visible")&&b.history_cache[d].dataset_ids.push(a.get("id"))})}var e=function(a,c){if(a){var d=b.history_cache[a.get("history_id")];if(d&&d.dataset_ids){var e=d.dataset_ids,f=e.indexOf(a.get("id"));if(f!==-1&&f+c>=0&&f+c<e.length)return e[f+c]}}},f=function(a,d,f){var g=e(a,d);g?b._loadDataset(g,function(a,b){c=a,f.model.set(b)}):f.model.trigger("change")};this._loadDataset(a,function(a,d){c=a,b.add(_.extend({menu:[{icon:"fa fa-chevron-circle-left",tooltip:"Previous in History",onclick:function(a){f(c,-1,a)},disabled:function(){return!e(c,-1)}},{icon:"fa fa-chevron-circle-right",tooltip:"Next in History",onclick:function(a){f(c,1,a)},disabled:function(){return!e(c,1)}}]},d))})},_loadDataset:function(a,b){var c=this;require(["mvc/dataset/data"],function(d){var e=new d.Dataset({id:a});$.when(e.fetch()).then(function(){var f=_.find(["tabular","interval"],function(a){return e.get("data_type").indexOf(a)!==-1}),g=e.get("name"),h=c.history_cache[e.get("history_id")];h&&(g=h.name+": "+g),b(e,f?{title:g,url:null,content:d.createTabularDatasetChunkedView({model:new d.TabularDataset(e.toJSON()),embedded:!0,height:"100%"}).$el}:{title:g,url:Galaxy.root+"datasets/"+a+"/display/?preview=True",content:null})})})},addTrackster:function(a){var b=this;require(["viz/visualization","viz/trackster"],function(c,d){var e=new c.Visualization({id:a});$.when(e.fetch()).then(function(){var a=new d.TracksterUI(Galaxy.root),c={title:e.get("name"),type:"other",content:function(b){var c={container:b,name:e.get("title"),id:e.id,dbkey:e.get("dbkey"),stand_alone:!1},d=e.get("latest_revision"),f=d.config.view.drawables;_.each(f,function(a){a.dataset={hda_ldda:a.hda_ldda,id:a.dataset_id}}),view=a.create_visualization(c,d.config.viewport,d.config.view.drawables,d.config.bookmarks,!1)}};b.add(c)})})},add:function(a){if("_blank"==a.target)window.open(a.url);else if("_top"==a.target||"_parent"==a.target||"_self"==a.target)window.location=a.url;else if(this.active)this.frames.add(a);else{var b=$(window.parent.document).find("#galaxy_main");"galaxy_main"==a.target||"center"==a.target?0===b.length?window.location=a.url+(href.indexOf("?")==-1?"?":"&")+"use_panels=True":b.attr("src",a.url):window.location=a.url}}})});
//# sourceMappingURL=../../maps/layout/scratchbook.js.map