define(["jquery","libs/underscore","libs/backbone","mvc/base-mvc"],function(a,b,c,d){"use strict";var e=a,f=160,g=800,h=c.View.extend(d.LoggableMixin).extend({_logNamespace:"layout",initialize:function(a){this.log(this+".initialize:",a),this.title=a.title||this.title||"",this.hidden=!1,this.savedSize=null,this.hiddenByTool=!1},$center:function(){return this.$el.siblings("#center")},$toggleButton:function(){return this.$(".unified-panel-footer > .panel-collapse")},render:function(){this.log(this+".render:"),this.$el.html(this.template(this.id))},template:function(){return[this._templateHeader(),this._templateBody(),this._templateFooter()].join("")},_templateHeader:function(a){return['<div class="unified-panel-header" unselectable="on">','<div class="unified-panel-header-inner">','<div class="panel-header-buttons" style="float: right"/>','<div class="panel-header-text">',b.escape(this.title),"</div>","</div>","</div>"].join("")},_templateBody:function(a){return'<div class="unified-panel-body"/>'},_templateFooter:function(a){return['<div class="unified-panel-footer">','<div class="panel-collapse ',b.escape(this.id),'"/>','<div class="drag"/>',"</div>"].join("")},events:{"mousedown .unified-panel-footer > .drag":"_mousedownDragHandler","click .unified-panel-footer > .panel-collapse":"toggle"},_mousedownDragHandler:function(a){function b(a){var b=a.pageX-h;h=a.pageX;var e=c.$el.width(),i=d?e+b:e-b;i=Math.min(g,Math.max(f,i)),c.resize(i)}var c=this,d="left"===this.id,h=a.pageX;e("#dd-helper").show().on("mousemove",b).one("mouseup",function(a){e(this).hide().off("mousemove",b)})},resize:function(a){return this.$el.css("width",a),this.$center().css(this.id,a),self},show:function(){if(this.hidden){var a=this,b={},c=this.id;return b[c]=0,a.$el.css(c,-this.savedSize).show().animate(b,"fast",function(){a.resize(a.savedSize)}),a.hidden=!1,a.$toggleButton().removeClass("hidden"),a}},hide:function(){if(!this.hidden){var a=this,b={},c=this.id;return a.savedSize=this.$el.width(),b[c]=-this.savedSize,this.$el.animate(b,"fast"),this.$center().css(c,0),a.hidden=!0,a.$toggleButton().addClass("hidden"),a}},toggle:function(a){var b=this;return b.hidden?b.show():b.hide(),b.hiddenByTool=!1,b},handle_minwidth_hint:function(a){var b=this.$center().width()-(this.hidden?this.savedSize:0);return b<a?this.hidden||(this.toggle(),this.hiddenByTool=!0):this.hiddenByTool&&(this.toggle(),this.hiddenByTool=!1),self},force_panel:function(a){return"show"==a?this.show():"hide"==a?this.hide():self},toString:function(){return"SidePanel("+this.id+")"}}),i=h.extend({id:"left"}),j=h.extend({id:"right"}),k=c.View.extend(d.LoggableMixin).extend({_logNamespace:"layout",initialize:function(a){this.log(this+".initialize:",a),this.prev=null},render:function(){this.log(this+".render:"),this.$el.html(this.template()),this.$("#galaxy_main").on("load",b.bind(this._iframeChangeHandler,this))},_iframeChangeHandler:function(a){var b=a.currentTarget,c=b.contentWindow&&b.contentWindow.location;c&&c.host&&(e(b).show(),this.prev&&this.prev.remove(),this.$("#center-panel").hide(),Galaxy.trigger("galaxy_main:load",{fullpath:c.pathname+c.search+c.hash,pathname:c.pathname,search:c.search,hash:c.hash}),this.trigger("galaxy_main:load",c))},display:function(a){var b=this.$("#galaxy_main")[0].contentWindow||{},c=b.onbeforeunload&&b.onbeforeunload();!c||confirm(c)?(b.onbeforeunload=void 0,this.prev&&this.prev.remove(),this.prev=a,this.$("#galaxy_main").attr("src","about:blank").hide(),this.$("#center-panel").scrollTop(0).append(a.$el).show(),this.trigger("center-panel:load",a)):a&&a.remove()},template:function(){return['<div style="position: absolute; width: 100%; height: 100%">','<iframe name="galaxy_main" id="galaxy_main" frameborder="0" ','style="position: absolute; width: 100%; height: 100%;"/>','<div id="center-panel" ','style="display: none; position: absolute; width: 100%; height: 100%; padding: 10px; overflow: auto;"/>',"</div>"].join("")},toString:function(){return"CenterPanel"}});return{LeftPanel:i,RightPanel:j,CenterPanel:k}});
//# sourceMappingURL=../../maps/layout/panel.js.map