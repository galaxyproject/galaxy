define("mvc/history/history-view-edit-current",["exports","mvc/history/history-model","mvc/history/history-view-edit","mvc/base-mvc","utils/localization"],function(e,t,n,o,i){"use strict";function s(e){return e&&e.__esModule?e:{default:e}}Object.defineProperty(e,"__esModule",{value:!0});s(t);var r=s(n),a=s(o),l=s(i),d=a.default.SessionStorageModel.extend({defaults:{tagsEditorShown:!1,annotationEditorShown:!1,scrollPosition:0},toString:function(){return"HistoryViewPrefs("+JSON.stringify(this.toJSON())+")"}});d.storageKey=function(){return"history-panel"};var u=r.default.HistoryViewEdit,c=u.extend({className:u.prototype.className+" current-history-panel",HDCAViewClass:u.prototype.HDCAViewClass.extend({foldoutStyle:"drilldown"}),emptyMsg:[(0,l.default)("This history is empty"),". ",(0,l.default)("You can "),'<a class="uploader-link" href="javascript:void(0)">',(0,l.default)("load your own data"),"</a>",(0,l.default)(" or "),'<a class="get-data-link" href="javascript:void(0)">',(0,l.default)("get data from an external source"),"</a>"].join(""),initialize:function(e){e=e||{},this.preferences=new d(_.extend({id:d.storageKey()},_.pick(e,_.keys(d.prototype.defaults)))),u.prototype.initialize.call(this,e),this.panelStack=[],this.currentContentId=e.currentContentId||null},_setUpListeners:function(){u.prototype._setUpListeners.call(this);var e=this;this.on("new-model",function(){e.preferences.set("scrollPosition",0)})},loadCurrentHistory:function(){return this.loadHistory(null,{url:Galaxy.root+"history/current_history_json"})},switchToHistory:function(e,t){return Galaxy.user.isAnonymous()?(this.trigger("error",(0,l.default)("You must be logged in to switch histories"),(0,l.default)("Anonymous user")),$.when()):this.loadHistory(e,{url:Galaxy.root+"history/set_as_current?id="+e})},createNewHistory:function(e){return Galaxy.user.isAnonymous()?(this.trigger("error",(0,l.default)("You must be logged in to create histories"),(0,l.default)("Anonymous user")),$.when()):this.loadHistory(null,{url:Galaxy.root+"history/create_new_current"})},setModel:function(e,t,n){return u.prototype.setModel.call(this,e,t,n),this.model&&this.model.id&&(this.log("checking for updates"),this.model.checkForUpdates()),this},_setUpModelListeners:function(){return u.prototype._setUpModelListeners.call(this),this.listenTo(this.model,{"change:nice_size change:size":function(){this.trigger("history-size-change",this,this.model,arguments)},"change:id":function(){this.once("loading-done",function(){this.model.checkForUpdates()})}})},_setUpCollectionListeners:function(){u.prototype._setUpCollectionListeners.call(this),this.listenTo(this.collection,"state:ready",function(e,t,n){e.get("visible")||this.collection.storage.includeHidden()||this.removeItemView(e)})},_setUpBehaviors:function(e){e=e||this.$el;var t=this;return u.prototype._setUpBehaviors.call(t,e),this._debouncedScrollCaptureHandler||(this._debouncedScrollCaptureHandler=_.debounce(function(){t.$el.is(":visible")&&t.preferences.set("scrollPosition",$(this).scrollTop())},40)),t.$scrollContainer(e).off("scroll",this._debouncedScrollCaptureHandler).on("scroll",this._debouncedScrollCaptureHandler),t},_buildNewRender:function(){if(!this.model)return $();var e=u.prototype._buildNewRender.call(this);return e.find(".search").prependTo(e.find("> .controls")),this._renderQuotaMessage(e),e},_renderQuotaMessage:function(e){return e=e||this.$el,$(this.templates.quotaMsg({},this)).prependTo(e.find(".messages"))},_renderTags:function(e){var t=this;u.prototype._renderTags.call(t,e),t.preferences.get("tagsEditorShown")&&t.tagsEditor.toggle(!0),t.listenTo(t.tagsEditor,"hiddenUntilActivated:shown hiddenUntilActivated:hidden",function(e){t.preferences.set("tagsEditorShown",e.hidden)})},_renderAnnotation:function(e){var t=this;u.prototype._renderAnnotation.call(t,e),t.preferences.get("annotationEditorShown")&&t.annotationEditor.toggle(!0),t.listenTo(t.annotationEditor,"hiddenUntilActivated:shown hiddenUntilActivated:hidden",function(e){t.preferences.set("annotationEditorShown",e.hidden)})},_swapNewRender:function(e){u.prototype._swapNewRender.call(this,e);var t=this;return _.delay(function(){var e=t.preferences.get("scrollPosition");e&&t.scrollTo(e,0)},10),this},_attachItems:function(e){u.prototype._attachItems.call(this,e);var t=this;return t.currentContentId&&t._setCurrentContentById(t.currentContentId),this},addItemView:function(e,t,n){var o=u.prototype.addItemView.call(this,e,t,n);return o&&this.panelStack.length?this._collapseDrilldownPanel():o},_setUpItemViewListeners:function(e){var t=this;return u.prototype._setUpItemViewListeners.call(t,e),t.listenTo(e,{"expanded:drilldown":function(e,t){this._expandDrilldownPanel(t)},"collapsed:drilldown":function(e,t){this._collapseDrilldownPanel(t)}})},setCurrentContent:function(e){this.$(".history-content.current-content").removeClass("current-content"),e?(e.$el.addClass("current-content"),this.currentContentId=e.model.id):this.currentContentId=null},_setCurrentContentById:function(e){var t=this.viewFromModelId(e)||null;this.setCurrentContent(t)},_expandDrilldownPanel:function(e){this.panelStack.push(e),this.$controls().add(this.$list()).hide(),e.parentName=this.model.get("name"),e.delegateEvents().render().$el.appendTo(this.$el)},_collapseDrilldownPanel:function(e){this.panelStack.pop(),this.$controls().add(this.$list()).show()},events:_.extend(_.clone(u.prototype.events),{"click .uploader-link":function(e){Galaxy.upload.show(e)},"click .get-data-link":function(e){var t=$(".toolMenuContainer");t.parent().scrollTop(0),t.find('span:contains("Get Data")').click()}}),listenToGalaxy:function(e){this.listenTo(e,{"center-frame:load":function(e){var t=e.fullpath,n=null,o={display:/datasets\/([a-f0-9]+)\/display/,edit:/datasets\/([a-f0-9]+)\/edit/,report_error:/dataset\/errors\?id=([a-f0-9]+)/,rerun:/tool_runner\/rerun\?id=([a-f0-9]+)/};_.find(o,function(e,o){return n=_.result(t.match(e),1)}),this._setCurrentContentById(n?"dataset-"+n:null)},"center-panel:load":function(e){this._setCurrentContentById()}})},connectToQuotaMeter:function(e){return e?(this.listenTo(e,"quota:over",this.showQuotaMessage),this.listenTo(e,"quota:under",this.hideQuotaMessage),this.on("rendered rendered:initial",function(){e&&e.isOverQuota()&&this.showQuotaMessage()}),this):this},clearMessages:function(e){var t=_.isUndefined(e)?this.$messages().children('[class$="message"]'):$(e.currentTarget);return(t=t.not(".quota-message")).fadeOut(this.fxSpeed,function(){$(this).remove()}),this},showQuotaMessage:function(){var e=this.$(".quota-message");e.is(":hidden")&&e.slideDown(this.fxSpeed)},hideQuotaMessage:function(){var e=this.$(".quota-message");e.is(":hidden")||e.slideUp(this.fxSpeed)},unhideHidden:function(){var e=this;return confirm((0,l.default)("Really unhide all hidden datasets?"))?e.model.contents._filterAndUpdate({visible:!1,deleted:"",purged:""},{visible:!0}).done(function(){e.model.contents.includeHidden||e.renderItems()}):jQuery.when()},deleteHidden:function(){var e=this;return confirm((0,l.default)("Really delete all hidden datasets?"))?e.model.contents._filterAndUpdate({visible:!1,deleted:"",purged:""},{deleted:!0,visible:!0}):jQuery.when()},toString:function(){return"CurrentHistoryView("+(this.model?this.model.get("name"):"")+")"}});c.prototype.templates=function(){var e=a.default.wrapTemplate(['<div class="quota-message errormessage">',(0,l.default)("You are over your disk quota"),". ",(0,l.default)("Tool execution is on hold until your disk usage drops below your allocated quota"),".","</div>"],"history");return _.extend(_.clone(u.prototype.templates),{quotaMsg:e})}(),e.default={CurrentHistoryView:c}});