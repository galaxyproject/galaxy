define(["mvc/ui/ui-modal","mvc/ui/ui-frames","mvc/ui/icon-button"],function(a,b,c){var d=Backbone.Model.extend({}),e=Backbone.Model.extend({defaults:{id:"",type:"",name:"",hda_ldda:"hda",metadata:null},initialize:function(){this.get("metadata")||this._set_metadata(),this.on("change",this._set_metadata,this)},_set_metadata:function(){var a=new d;_.each(_.keys(this.attributes),function(b){if(0===b.indexOf("metadata_")){var c=b.split("metadata_")[1];a.set(c,this.attributes[b]),delete this.attributes[b]}},this),this.set("metadata",a,{silent:!0})},get_metadata:function(a){return this.attributes.metadata.get(a)},urlRoot:Galaxy.root+"api/datasets"}),f=e.extend({defaults:_.extend({},e.prototype.defaults,{chunk_url:null,first_data_chunk:null,offset:0,at_eof:!1}),initialize:function(){e.prototype.initialize.call(this),this.attributes.first_data_chunk&&(this.attributes.offset=this.attributes.first_data_chunk.offset),this.attributes.chunk_url=Galaxy.root+"dataset/display?dataset_id="+this.id,this.attributes.url_viz=Galaxy.root+"visualization"},get_next_chunk:function(){if(this.attributes.at_eof)return null;var a=this,b=$.Deferred();return $.getJSON(this.attributes.chunk_url,{offset:a.attributes.offset}).success(function(c){var d;""!==c.ck_data?(d=c,a.attributes.offset=c.offset):(a.attributes.at_eof=!0,d=null),b.resolve(d)}),b}}),g=Backbone.Collection.extend({model:e}),h=Backbone.View.extend({initialize:function(a){this.row_count=0,this.loading_chunk=!1,new l({model:a.model,$el:this.$el})},expand_to_container:function(){this.$el.height()<this.scroll_elt.height()&&this.attempt_to_fetch()},attempt_to_fetch:function(){var a=this;!this.loading_chunk&&this.scrolled_to_bottom()&&(this.loading_chunk=!0,this.loading_indicator.show(),$.when(a.model.get_next_chunk()).then(function(b){b&&(a._renderChunk(b),a.loading_chunk=!1),a.loading_indicator.hide(),a.expand_to_container()}))},render:function(){this.loading_indicator=$("<div/>").attr("id","loading_indicator"),this.$el.append(this.loading_indicator);var a=$("<table/>").attr({id:"content_table",cellpadding:0});this.$el.append(a);var b=this.model.get_metadata("column_names"),c=$("<thead/>").appendTo(a),d=$("<tr/>").appendTo(c);if(b)d.append("<th>"+b.join("</th><th>")+"</th>");else for(var e=1;e<=this.model.get_metadata("columns");e++)d.append("<th>"+e+"</th>");var f=this,g=this.model.get("first_data_chunk");g?this._renderChunk(g):$.when(f.model.get_next_chunk()).then(function(a){f._renderChunk(a)}),this.scroll_elt.scroll(function(){f.attempt_to_fetch()})},scrolled_to_bottom:function(){return!1},_renderCell:function(a,b,c){var d=$("<td>").text(a),e=this.model.get_metadata("column_types");return void 0!==c?d.attr("colspan",c).addClass("stringalign"):e&&b<e.length&&("str"===e[b]||"list"===e[b])&&d.addClass("stringalign"),d},_renderRow:function(a){var b=a.split("	"),c=$("<tr>"),d=this.model.get_metadata("columns");return this.row_count%2!==0&&c.addClass("dark_row"),b.length===d?_.each(b,function(a,b){c.append(this._renderCell(a,b))},this):b.length>d?(_.each(b.slice(0,d-1),function(a,b){c.append(this._renderCell(a,b))},this),c.append(this._renderCell(b.slice(d-1).join("	"),d-1))):1===b.length?(""==a&&(a="Blank line"),c.append(this._renderCell(a,0,d))):(_.each(b,function(a,b){c.append(this._renderCell(a,b))},this),_.each(_.range(d-b.length),function(){c.append($("<td>"))})),this.row_count++,c},_renderChunk:function(a){var b=this.$el.find("table"),c=a.ck_data.split("\n"),d=c.length-1;for(i=0;i<d;i++)b.append(this._renderRow(c[i]))}}),j=h.extend({initialize:function(a){h.prototype.initialize.call(this,a),scroll_elt=_.find(this.$el.parents(),function(a){return"auto"===$(a).css("overflow")}),scroll_elt||(scroll_elt=window),this.scroll_elt=$(scroll_elt)},scrolled_to_bottom:function(){return this.$el.height()-this.scroll_elt.scrollTop()-this.scroll_elt.height()<=0}}),k=h.extend({initialize:function(a){h.prototype.initialize.call(this,a),this.scroll_elt=this.$el.css({position:"relative",overflow:"scroll",height:a.height||"500px"})},scrolled_to_bottom:function(){return this.$el.scrollTop()+this.$el.innerHeight()>=this.el.scrollHeight}}),l=Backbone.View.extend({col:{chrom:null,start:null,end:null},url_viz:null,dataset_id:null,genome_build:null,file_ext:null,initialize:function(a){function b(a,b){for(var c=0;c<b.length;c++)if(b[c].match(a))return c;return-1}var d=parent.Galaxy;if(d&&d.modal&&(this.modal=d.modal),d&&d.frame&&(this.frame=d.frame),this.modal&&this.frame){var e=a.model,f=e.get("metadata");if(e.get("file_ext")){if(this.file_ext=e.get("file_ext"),"bed"==this.file_ext){if(!(f.get("chromCol")&&f.get("startCol")&&f.get("endCol")))return void console.log("TabularButtonTrackster : Bed-file metadata incomplete.");this.col.chrom=f.get("chromCol")-1,this.col.start=f.get("startCol")-1,this.col.end=f.get("endCol")-1}if("vcf"==this.file_ext&&(this.col.chrom=b("Chrom",f.get("column_names")),this.col.start=b("Pos",f.get("column_names")),this.col.end=null,-1==this.col.chrom||-1==this.col.start))return void console.log("TabularButtonTrackster : VCF-file metadata incomplete.");if(void 0!==this.col.chrom){if(!e.id)return void console.log("TabularButtonTrackster : Dataset identification is missing.");if(this.dataset_id=e.id,!e.get("url_viz"))return void console.log("TabularButtonTrackster : Url for visualization controller is missing.");this.url_viz=e.get("url_viz"),e.get("genome_build")&&(this.genome_build=e.get("genome_build"));var g=new c.IconButtonView({model:new c.IconButton({title:"Visualize",icon_class:"chart_curve",id:"btn_viz"})});this.setElement(a.$el),this.$el.append(g.render().$el),this.hide()}}}},events:{"mouseover tr":"show",mouseleave:"hide"},show:function(a){function b(a){return!isNaN(parseFloat(a))&&isFinite(a)}if(null!==this.col.chrom){var c=$(a.target).parent(),d=c.children().eq(this.col.chrom).html(),e=c.children().eq(this.col.start).html(),f=this.col.end?c.children().eq(this.col.end).html():e;if(!d.match("^#")&&""!==d&&b(e)){var g={dataset_id:this.dataset_id,gene_region:d+":"+e+"-"+f},h=c.offset(),i=h.left-10,j=h.top-$(window).scrollTop()+3;$("#btn_viz").css({position:"fixed",top:j+"px",left:i+"px"}),$("#btn_viz").off("click"),$("#btn_viz").click(this.create_trackster_action(this.url_viz,g,this.genome_build)),$("#btn_viz").show()}else $("#btn_viz").hide()}},hide:function(){this.$el.find("#btn_viz").hide()},create_trackster_action:function(a,b,c){var d=this;return function(){var e={};return c&&(e["f-dbkey"]=c),$.ajax({url:a+"/list_tracks?"+$.param(e),dataType:"html",error:function(){d.modal.show({title:"Something went wrong!",body:"Unfortunately we could not add this dataset to the track browser. Please try again or contact us.",buttons:{Cancel:function(){d.modal.hide()}}})},success:function(c){d.modal.show({title:"View Data in a New or Saved Visualization",buttons:{Cancel:function(){d.modal.hide()},"View in saved visualization":function(){d.modal.show({title:"Add Data to Saved Visualization",body:c,buttons:{Cancel:function(){d.modal.hide()},"Add to visualization":function(){d.modal.hide(),d.modal.$el.find("input[name=id]:checked").each(function(){var c=$(this).val();b.id=c,d.frame.add({title:"Trackster",type:"url",content:a+"/trackster?"+$.param(b)})})}}})},"View in new visualization":function(){d.modal.hide(),d.frame.add({title:"Trackster",type:"url",content:a+"/trackster?"+$.param(b)})}}})}}),!1}}}),m=function(a){a.model||(a.model=new f(a.dataset_config));var b=a.parent_elt,c=a.embedded;delete a.embedded,delete a.parent_elt,delete a.dataset_config;var d=c?new k(a):new j(a);return d.render(),b&&(b.append(d.$el),d.expand_to_container()),d};return{Dataset:e,TabularDataset:f,DatasetCollection:g,TabularDatasetChunkedView:h,createTabularDatasetChunkedView:m}});
//# sourceMappingURL=../../../maps/mvc/dataset/data.js.map