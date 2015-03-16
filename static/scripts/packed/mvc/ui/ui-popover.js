define(["utils/utils"],function(a){var b=Backbone.View.extend({optionsDefault:{with_close:true,container:"body",title:null,placement:"top"},visible:false,initialize:function(d){var c=this;this.options=_.defaults(d,this.optionsDefault);this.setElement(this._template(this.options));this.options.container.parent().append(this.$el);if(this.options.with_close){this.$el.find("#close").on("click",function(){c.hide()})}this.uid=a.uid();var c=this;$("body").on("mousedown."+this.uid,function(f){c._hide(f)})},title:function(c){if(c!==undefined){this.$el.find(".popover-title-label").html(c)}},show:function(){this.$el.show();this.visible=true;var c=this._get_placement(this.options.placement);this.$el.css(c)},_get_placement:function(h){var d=this._get_width(this.$el);var j=this.$el.height();var k=this.options.container;var c=this._get_width(k);var f=this._get_height(k);var g=k.position();var i=0;var e=0;if(h=="top"||h=="bottom"){e=g.left-d+(c+d)/2;if(h=="top"){i=g.top-j-5}else{i=g.top+f+5}}return{top:i,left:e}},_get_width:function(c){return c.width()+parseInt(c.css("padding-left"))+parseInt(c.css("padding-right"))},_get_height:function(c){return c.height()+parseInt(c.css("padding-top"))+parseInt(c.css("padding-bottom"))},hide:function(){this.$el.hide();this.visible=false},append:function(c){this.$el.find(".popover-content").append(c)},empty:function(c){this.$el.find(".popover-content").empty()},remove:function(){$("body").off("mousedown."+this.uid);this.$el.remove()},_hide:function(c){if(!$(this.options.container).is(c.target)&&!$(this.el).is(c.target)&&$(this.el).has(c.target).length===0){this.hide()}},_template:function(d){var c='<div class="ui-popover popover fade '+d.placement+' in"><div class="arrow"></div><div class="popover-title"><div class="popover-title-label">'+d.title+"</div>";if(d.with_close){c+='<div id="close" class="popover-close fa fa-times-circle"></div>'}c+='</div><div class="popover-content"></div></div>';return c}});return{View:b}});