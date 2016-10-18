jQuery.ajaxSettings.traditional=!0,define(["mvc/grid/grid-model","mvc/grid/grid-template","mvc/ui/popup-menu"],function(a,b,c){return Backbone.View.extend({grid:null,initialize:function(a){this.setElement("#grid-container"),a.use_panels&&$("#center").css({padding:"10px",overflow:"auto"}),this.init_grid(a)},handle_refresh:function(a){a&&$.inArray("history",a)>-1&&top.Galaxy&&top.Galaxy.currHistoryPanel&&top.Galaxy.currHistoryPanel.loadCurrentHistory()},init_grid:function(c){this.grid=new a(c);var d=this.grid.attributes;this.handle_refresh(d.refresh_frames);var e=this.grid.get("url_base");if(e=e.replace(/^.*\/\/[^\/]+/,""),this.grid.set("url_base",e),this.$el.html(b.grid(d)),this.$el.find("#grid-table-header").html(b.header(d)),this.$el.find("#grid-table-body").html(b.body(d)),this.$el.find("#grid-table-footer").html(b.footer(d)),d.message){this.$el.find("#grid-message").html(b.message(d));var f=this;d.use_hide_message&&setTimeout(function(){f.$el.find("#grid-message").html("")},5e3)}this.init_grid_elements(),this.init_grid_controls(),init_refresh_on_change()},init_grid_controls:function(){var a=this;this.$el.find(".operation-button").each(function(){$(this).off(),$(this).click(function(){return a.submit_operation(this),!1})}),this.$el.find("input[type=text]").each(function(){$(this).off(),$(this).click(function(){$(this).select()}).keyup(function(){$(this).css("font-style","normal")})}),this.$el.find(".sort-link").each(function(){$(this).off(),$(this).click(function(){return a.set_sort_condition($(this).attr("sort_key")),!1})}),this.$el.find(".text-filter-form").each(function(){$(this).off(),$(this).submit(function(){var b=$(this).attr("column_key"),c=$("#input-"+b+"-filter"),d=c.val();return c.val(""),a.add_filter_condition(b,d),!1})}),this.$el.find(".text-filter-val > a").each(function(){$(this).off(),$(this).click(function(){return $(this).parent().remove(),a.remove_filter_condition($(this).attr("filter_key"),$(this).attr("filter_val")),!1})}),this.$el.find(".categorical-filter > a").each(function(){$(this).off(),$(this).click(function(){return a.set_categorical_filter($(this).attr("filter_key"),$(this).attr("filter_val")),!1})});var b=this.$el.find("#input-tags-filter");b.length&&b.autocomplete(this.grid.history_tag_autocomplete_url,{selectFirst:!1,autoFill:!1,highlight:!1,mustMatch:!1});var c=this.$el.find("#input-name-filter");c.length&&c.autocomplete(this.grid.history_name_autocomplete_url,{selectFirst:!1,autoFill:!1,highlight:!1,mustMatch:!1}),this.$el.find(".advanced-search-toggle").each(function(){$(this).off(),$(this).click(function(){return a.$el.find("#standard-search").slideToggle("fast"),a.$el.find("#advanced-search").slideToggle("fast"),!1})}),this.$el.find("#check_all").off(),this.$el.find("#check_all").on("click",function(){a.check_all_items()})},init_grid_elements:function(){this.$el.find(".grid").each(function(){var a=$(this).find("input.grid-row-select-checkbox"),b=$(this).find("span.grid-selected-count"),c=function(){b.text($(a).filter(":checked").length)};$(a).each(function(){$(this).change(c)}),c()}),0!==this.$el.find(".community_rating_star").length&&this.$el.find(".community_rating_star").rating({});var a=this.grid.attributes,b=this;this.$el.find(".page-link > a").each(function(){$(this).click(function(){return b.set_page($(this).attr("page_num")),!1})}),this.$el.find(".use-inbound").each(function(){$(this).click(function(a){return b.execute({href:$(this).attr("href"),inbound:!0}),!1})}),this.$el.find(".use-outbound").each(function(){$(this).click(function(a){return b.execute({href:$(this).attr("href")}),!1})});var d=a.items.length;if(0!=d)for(var e in a.items){var f=a.items[e],g=this.$el.find("#grid-"+e+"-popup");g.off();var h=new c(g);for(var i in a.operations){var j=a.operations[i],k=j.label,l=f.operation_config[k];f.encode_id;if(l.allowed&&j.allow_popup){var m={html:j.label,href:l.url_args,target:l.target,confirmation_text:j.confirm,inbound:j.inbound};m.func=function(a){a.preventDefault();var c=$(a.target).html(),d=this.findItemByHtml(c);b.execute(d)},h.addItem(m)}}}},add_filter_condition:function(a,c){if(""===c)return!1;this.grid.add_filter(a,c,!0);var d=$(b.filter_element(a,c)),e=this;d.click(function(){$(this).remove(),e.remove_filter_condition(a,c)});var f=this.$el.find("#"+a+"-filtering-criteria");f.append(d),this.go_page_one(),this.execute()},remove_filter_condition:function(a,b){this.grid.remove_filter(a,b),this.go_page_one(),this.execute()},set_sort_condition:function(a){var b=this.grid.get("sort_key"),c=a;b.indexOf(a)!==-1&&"-"!==b.substring(0,1)&&(c="-"+a),this.$el.find(".sort-arrow").remove();var d="-"==c.substring(0,1)?"&uarr;":"&darr;",e=$("<span>"+d+"</span>").addClass("sort-arrow");this.$el.find("#"+a+"-header").append(e),this.grid.set("sort_key",c),this.go_page_one(),this.execute()},set_categorical_filter:function(a,b){var c=this.grid.get("categorical_filters")[a],d=this.grid.get("filters")[a],e=this;this.$el.find("."+a+"-filter").each(function(){var f=$.trim($(this).text()),g=c[f],h=g[a];if(h==b)$(this).empty(),$(this).addClass("current-filter"),$(this).append(f);else if(h==d){$(this).empty();var i=$('<a href="#">'+f+"</a>");i.click(function(){e.set_categorical_filter(a,h)}),$(this).removeClass("current-filter"),$(this).append(i)}}),this.grid.add_filter(a,b),this.go_page_one(),this.execute()},set_page:function(a){var b=this;this.$el.find(".page-link").each(function(){var c,d=$(this).attr("id"),e=parseInt(d.split("-")[2],10),f=b.grid.get("cur_page");if(e===a)c=$(this).children().text(),$(this).empty(),$(this).addClass("inactive-link"),$(this).text(c);else if(e===f){c=$(this).text(),$(this).empty(),$(this).removeClass("inactive-link");var g=$('<a href="#">'+c+"</a>");g.click(function(){b.set_page(e)}),$(this).append(g)}}),"all"===a?this.grid.set("cur_page",a):this.grid.set("cur_page",parseInt(a,10)),this.execute()},submit_operation:function(a,b){var c=$(a).val(),d=this.$el.find('input[name="id"]:checked').length;if(!d>0)return!1;var e=_.findWhere(this.grid.attributes.operations,{label:c});e&&!b&&(b=e.confirm||"");var f=[];return this.$el.find("input[name=id]:checked").each(function(){f.push($(this).val())}),this.execute({operation:c,id:f,confirmation_text:b}),!0},check_all_items:function(){var a,b=document.getElementById("check_all"),c=document.getElementsByTagName("input"),d=0;if(b.checked===!0)for(a=0;a<c.length;a++)c[a].name.indexOf("id")!==-1&&(c[a].checked=!0,d++);else for(a=0;a<c.length;a++)c[a].name.indexOf("id")!==-1&&(c[a].checked=!1);this.init_grid_elements()},go_page_one:function(){var a=this.grid.get("cur_page");null!==a&&void 0!==a&&"all"!==a&&this.grid.set("cur_page",1)},execute:function(a){var b=null,c=null,d=null,e=null,f=null;if(a&&(c=a.href,d=a.operation,b=a.id,e=a.confirmation_text,f=a.inbound,void 0!==c&&c.indexOf("operation=")!=-1)){var g=c.split("?");if(g.length>1)for(var h=g[1],i=h.split("&"),j=0;j<i.length;j++)i[j].indexOf("operation")!=-1?(d=i[j].split("=")[1],d=d.replace(/\+/g," ")):i[j].indexOf("id")!=-1&&(b=i[j].split("=")[1])}return d&&b?!(e&&""!=e&&"None"!=e&&"null"!=e&&!confirm(e))&&(d=d.toLowerCase(),this.grid.set({operation:d,item_ids:b}),this.grid.can_async_op(d)?this.update_grid():this.go_to(f,c),!1):c?(this.go_to(f,c),!1):(this.grid.get("async")?this.update_grid():this.go_to(f,c),!1)},go_to:function(a,b){var c=this.grid.get("async");if(this.grid.set("async",!1),advanced_search=this.$el.find("#advanced-search").is(":visible"),this.grid.set("advanced_search",advanced_search),b||(b=this.grid.get("url_base")+"?"+$.param(this.grid.get_url_data())),this.grid.set({operation:void 0,item_ids:void 0,async:c}),a){var d=$(".grid-header").closest(".inbound");if(0!==d.length)return void d.load(b)}window.location=b},update_grid:function(){var a=this.grid.get("operation")?"POST":"GET";this.$el.find(".loading-elt-overlay").show();var b=this;$.ajax({type:a,url:b.grid.get("url_base"),data:b.grid.get_url_data(),error:function(a){alert("Grid refresh failed")},success:function(a){var c=b.grid.get("embedded"),d=b.grid.get("insert"),e=$.parseJSON(a);e.embedded=c,e.insert=d,b.init_grid(e),b.$el.find(".loading-elt-overlay").hide()},complete:function(){b.grid.set({operation:void 0,item_ids:void 0})}})}})});
//# sourceMappingURL=../../../maps/mvc/grid/grid-view.js.map