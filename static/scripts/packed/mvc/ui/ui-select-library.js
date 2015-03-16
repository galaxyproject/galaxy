define(["utils/utils","mvc/ui/ui-misc","mvc/ui/ui-tabs","mvc/tools/tools-template"],function(e,g,b,a){var d=Backbone.Collection.extend({url:galaxy_config.root+"api/libraries"});var c=Backbone.Collection.extend({initialize:function(){var h=this;this.config=new Backbone.Model({library_id:null});this.config.on("change",function(){h.fetch({reset:true})})},url:function(){return galaxy_config.root+"api/libraries/"+this.config.get("library_id")+"/contents"}});var f=Backbone.View.extend({initialize:function(i){var h=this;this.libraries=new d();this.datasets=new c();this.options=i;this.library_select=new g.Select.View({optional:i.optional,onchange:function(j){h.datasets.config.set("library_id",j)}});this.dataset_select=new g.Select.View({optional:i.optional,multiple:i.multiple,onchange:function(){h.trigger("change")}});this.libraries.on("reset",function(){var j=[];h.libraries.each(function(k){j.push({value:k.id,label:k.get("name")})});h.library_select.update(j);h.trigger("change")});this.datasets.on("reset",function(){var k=[];var j=h.library_select.text();if(j!==null){h.datasets.each(function(l){if(l.get("type")==="file"){k.push({value:l.id,label:j+l.get("name")})}})}h.dataset_select.update(k);h.trigger("change")});this.on("change",function(){i.onchange&&i.onchange(h.value())});this.setElement(this._template());this.$(".library-select").append(this.library_select.$el);this.$(".dataset-select").append(this.dataset_select.$el);this.libraries.fetch({reset:true,success:function(){h.library_select.trigger("change");if(h.options.value!==undefined){h.value(h.options.value)}}})},value:function(h){return this.dataset_select.value()},_template:function(){return'<div class="ui-select-library"><div class="library ui-margin-bottom"><span class="library-title">Select Library</span><span class="library-select"/></div><div class="dataset"><span class="dataset-title">Select Dataset</span><span class="dataset-select"/></div></div>'}});return{View:f}});