define(["utils/utils"],function(a){var b=Backbone.View.extend({optionsDefault:{css:"",placeholder:"No data available",data:[],value:null,multiple:!1,minimumInputLength:0,initialData:"",allowClear:!1},initialize:function(b){if(this.options=a.merge(b,this.optionsDefault),this.setElement(this._template(this.options)),!this.options.container)return void console.log("ui-select::initialize() : container not specified.");if(this.options.container.append(this.$el),this.select_data=this.options.data,this._refresh(),!this.options.multiple){this.options.value&&this._setValue(this.options.value);var c=this;this.options.onchange&&this.$el.on("change",function(){c.options.onchange(c.value())})}},value:function(a){var b=this._getValue();void 0!==a&&this._setValue(a);var c=this._getValue();return c!=b&&this.options.onchange&&this.options.onchange(c),c},text:function(){return this.$el.select2("data").text},disabled:function(){return!this.$el.select2("enable")},enable:function(){this.$el.select2("enable",!0)},disable:function(){this.$el.select2("enable",!1)},add:function(a){this.select_data.push({id:a.id,text:a.text}),this._refresh()},del:function(a){var b=this._getIndex(a);-1!=b&&(this.select_data.splice(b,1),this._refresh())},remove:function(){this.$el.select2("destroy")},update:function(a){this.select_data=[];for(var b in a.data)this.select_data.push(a.data[b]);this._refresh()},_refresh:function(){if(this.options.multiple){var a={multiple:this.options.multiple,containerCssClass:this.options.css,placeholder:this.options.placeholder,minimumInputLength:this.options.minimumInputLength,ajax:this.options.ajax,dropdownCssClass:this.options.dropdownCssClass,escapeMarkup:this.options.escapeMarkup,formatResult:this.options.formatResult,formatSelection:this.options.formatSelection,initSelection:this.options.initSelection,initialData:this.options.initialData};this.$el.select2(a)}else{var b=this._getValue(),a={data:this.select_data,containerCssClass:this.options.css,placeholder:this.options.placeholder,dropdownAutoWidth:!0,allowClear:this.options.allowClear};this.$el.select2(a),this._setValue(b)}},_getIndex:function(a){for(var b in this.select_data)if(this.select_data[b].id==a)return b;return-1},_getValue:function(){return this.$el.select2("val")},_setValue:function(a){var b=this._getIndex(a);-1==b&&this.select_data.length>0&&(a=this.select_data[0].id),this.$el.select2("val",a)},_template:function(){return'<input type="hidden" value="'+this.options.initialData+'"/>'}});return{View:b}});
//# sourceMappingURL=../../../maps/mvc/ui/ui-select.js.map