define(["libs/underscore","viz/trackster/util","utils/config"],function(a,b,c){var d=Backbone.Model.extend({initialize:function(c){var e=this.get("key");this.set("id",e);var f=a.find(d.known_settings_defaults,function(a){return a.key===e});f&&this.set(a.extend({},f,c)),void 0===this.get("value")&&void 0!==this.get("default_value")&&(this.set_value(this.get("default_value")),this.get("value")||"color"!==this.get("type")||this.set("value",b.get_random_color()))},set_value:function(a,b){var c=this.get("type");"float"===c?a=parseFloat(a):"int"===c&&(a=parseInt(a,10)),this.set({value:a},b)}},{known_settings_defaults:[{key:"name",label:"Name",type:"text",default_value:""},{key:"color",label:"Color",type:"color",default_value:null},{key:"min_value",label:"Min Value",type:"float",default_value:null},{key:"max_value",label:"Max Value",type:"float",default_value:null},{key:"mode",type:"string",default_value:this.mode,hidden:!0},{key:"height",type:"int",default_value:32,hidden:!0},{key:"pos_color",label:"Positive Color",type:"color",default_value:"#FF8C00"},{key:"neg_color",label:"Negative Color",type:"color",default_value:"#4169E1"},{key:"block_color",label:"Block color",type:"color",default_value:null},{key:"label_color",label:"Label color",type:"color",default_value:"black"},{key:"show_insertions",label:"Show insertions",type:"bool",default_value:!1},{key:"show_counts",label:"Show summary counts",type:"bool",default_value:!0},{key:"mode",type:"string",default_value:this.mode,hidden:!0},{key:"reverse_strand_color",label:"Antisense strand color",type:"color",default_value:null},{key:"show_differences",label:"Show differences only",type:"bool",default_value:!0},{key:"mode",type:"string",default_value:this.mode,hidden:!0}]}),e=Backbone.Collection.extend({model:d,to_key_value_dict:function(){var a={};return this.each(function(b){a[b.get("key")]=b.get("value")}),a},get_value:function(a){var b=this.get(a);if(b)return b.get("value")},set_value:function(a,b,c){var d=this.get(a);if(d)return d.set_value(b,c)},set_default_value:function(a,b){var c=this.get(a);if(c)return c.set("default_value",b)}},{from_models_and_saved_values:function(b,c){return c&&(b=a.map(b,function(b){return a.extend({},b,{value:c[b.key]})})),new e(b)}}),f=Backbone.View.extend({className:"config-settings-view",render:function(){var c=this.$el;return this.collection.each(function(d,e){if(!d.get("hidden")){var f="param_"+e,g=d.get("type"),h=d.get("value"),i=$("<div class='form-row' />").appendTo(c);if(i.append($("<label />").attr("for",f).text(d.get("label")+":")),"bool"===g)i.append($('<input type="checkbox" />').attr("id",f).attr("name",f).attr("checked",h));else if("text"===g)i.append($('<input type="text"/>').attr("id",f).val(h).click(function(){$(this).select()}));else if("select"===g){var j=$("<select />").attr("id",f);a.each(d.get("options"),function(a){$("<option/>").text(a.label).attr("value",a.value).appendTo(j)}),j.val(h),i.append(j)}else if("color"===g){var k=$("<div/>").appendTo(i),l=$("<input />").attr("id",f).attr("name",f).val(h).css("float","left").appendTo(k).click(function(a){$(".tooltip").removeClass("in");var b=$(this).siblings(".tooltip").addClass("in");b.css({left:$(this).position().left+$(this).width()+5,top:$(this).position().top-$(b).height()/2+$(this).height()/2}).show(),b.click(function(a){a.stopPropagation()}),$(document).bind("click.color-picker",function(){b.hide(),$(document).unbind("click.color-picker")}),a.stopPropagation()}),m=$("<a href='javascript:void(0)'/>").addClass("icon-button arrow-circle").appendTo(k).attr("title","Set new random color").tooltip(),n=$("<div class='tooltip right' style='position: absolute;' />").appendTo(k).hide(),o=$("<div class='tooltip-inner' style='text-align: inherit'></div>").appendTo(n),p=($("<div class='tooltip-arrow'></div>").appendTo(n),$.farbtastic(o,{width:100,height:100,callback:l,color:h}));k.append($("<div/>").css("clear","both")),function(a){m.click(function(){a.setColor(b.get_random_color())})}(p)}else i.append($("<input />").attr("id",f).attr("name",f).val(h));d.help&&i.append($("<div class='help'/>").text(d.help))}}),this},render_in_modal:function(a){var b=this,c=function(){Galaxy.modal.hide(),$(window).unbind("keypress.check_enter_esc")},d=function(){Galaxy.modal.hide(),$(window).unbind("keypress.check_enter_esc"),b.update_from_form()},e=function(a){27===(a.keyCode||a.which)?c():13===(a.keyCode||a.which)&&d()};$(window).bind("keypress.check_enter_esc",e),0===this.$el.children().length&&this.render(),Galaxy.modal.show({title:a||"Configure",body:this.$el,buttons:{Cancel:c,OK:d}})},update_from_form:function(){var a=this;this.collection.each(function(b,c){if(!b.get("hidden")){var d="param_"+c,e=a.$el.find("#"+d).val();"bool"===b.get("type")&&(e=a.$el.find("#"+d).is(":checked")),b.set_value(e)}})}});return{ConfigSetting:d,ConfigSettingCollection:e,ConfigSettingCollectionView:f}});
//# sourceMappingURL=../../maps/utils/config.js.map