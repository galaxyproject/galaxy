define(["libs/toastr","mvc/library/library-model","utils/utils","mvc/ui/ui-select"],function(a,b,c,d){var e=Backbone.View.extend({el:"#center",model:null,options:{},events:{"click .toolbtn_modify_dataset":"enableModification","click .toolbtn_cancel_modifications":"render","click .toolbtn-download-dataset":"downloadDataset","click .toolbtn-import-dataset":"importIntoHistory","click .toolbtn-share-dataset":"shareDataset","click .btn-copy-link-to-clipboard":"copyToClipboard","click .btn-make-private":"makeDatasetPrivate","click .btn-remove-restrictions":"removeDatasetRestrictions","click .toolbtn_save_permissions":"savePermissions","click .toolbtn_save_modifications":"comingSoon"},select_genome:null,select_extension:null,list_extensions:[],auto:{id:"auto",text:"Auto-detect",description:"This system will try to detect the file type automatically. If your file is not detected properly as one of the known formats, it most likely means that it has some format problems (e.g., different number of columns on different rows). You can still coerce the system to set your data to the format you think it should be. You can also upload compressed files, which will automatically be decompressed."},list_genomes:[],initialize:function(a){this.options=_.extend(this.options,a),this.fetchExtAndGenomes(),this.options.id&&this.fetchDataset()},fetchDataset:function(c){this.options=_.extend(this.options,c),this.model=new b.Item({id:this.options.id});var d=this;this.model.fetch({success:function(){d.options.show_permissions?d.showPermissions():d.options.show_version?d.fetchVersion():d.render()},error:function(b,c){"undefined"!=typeof c.responseJSON?a.error(c.responseJSON.err_msg+" Click this to go back.","",{onclick:function(){Galaxy.libraries.library_router.back()}}):a.error("An error ocurred. Click this to go back.","",{onclick:function(){Galaxy.libraries.library_router.back()}})}})},render:function(a){this.options=_.extend(this.options,a),$(".tooltip").remove();var b=this.templateDataset();this.$el.html(b({item:this.model})),$(".peek").html(this.model.get("peek")),$("#center [data-toggle]").tooltip()},fetchVersion:function(c){this.options=_.extend(this.options,c),that=this,this.options.ldda_id?(this.ldda=new b.Ldda({id:this.options.ldda_id}),this.ldda.url=this.ldda.urlRoot+this.model.id+"/versions/"+this.ldda.id,this.ldda.fetch({success:function(){that.renderVersion()},error:function(b,c){"undefined"!=typeof c.responseJSON?a.error(c.responseJSON.err_msg):a.error("An error ocurred.")}})):(this.render(),a.error("Library dataset version requested but no id provided."))},renderVersion:function(){$(".tooltip").remove();var a=this.templateVersion();this.$el.html(a({item:this.model,ldda:this.ldda})),$(".peek").html(this.ldda.get("peek"))},enableModification:function(){$(".tooltip").remove();var a=this.templateModifyDataset();this.$el.html(a({item:this.model})),this.renderSelectBoxes({genome_build:this.model.get("genome_build"),file_ext:this.model.get("file_ext")}),$(".peek").html(this.model.get("peek")),$("#center [data-toggle]").tooltip()},downloadDataset:function(){var a=Galaxy.root+"api/libraries/datasets/download/uncompressed",b={ld_ids:this.id};this.processDownload(a,b)},processDownload:function(b,c,d){if(b&&c){c="string"==typeof c?c:$.param(c);var e="";$.each(c.split("&"),function(){var a=this.split("=");e+='<input type="hidden" name="'+a[0]+'" value="'+a[1]+'" />'}),$('<form action="'+b+'" method="'+(d||"post")+'">'+e+"</form>").appendTo("body").submit().remove(),a.info("Your download will begin soon.")}},importIntoHistory:function(){this.refreshUserHistoriesList(function(a){var b=a.templateBulkImportInModal();a.modal=Galaxy.modal,a.modal.show({closing_events:!0,title:"Import into History",body:b({histories:a.histories.models}),buttons:{Import:function(){a.importCurrentIntoHistory()},Close:function(){Galaxy.modal.hide()}}})})},refreshUserHistoriesList:function(c){var d=this;this.histories=new b.GalaxyHistories,this.histories.fetch({success:function(b){0===b.length?a.warning("You have to create history first. Click this to do so.","",{onclick:function(){window.location="/"}}):c(d)},error:function(b,c){"undefined"!=typeof c.responseJSON?a.error(c.responseJSON.err_msg):a.error("An error ocurred.")}})},importCurrentIntoHistory:function(){this.modal.disableButton("Import");var b=this.modal.$("input[name=history_name]").val(),c=this;if(""!==b)$.post(Galaxy.root+"api/histories",{name:b}).done(function(a){c.processImportToHistory(a.id)}).fail(function(b,c,d){a.error("An error ocurred.")}).always(function(){c.modal.enableButton("Import")});else{var d=$(this.modal.$el).find("select[name=dataset_import_single] option:selected").val();this.processImportToHistory(d),this.modal.enableButton("Import")}},processImportToHistory:function(c){var d=new b.HistoryItem;d.url=d.urlRoot+c+"/contents",jQuery.getJSON(Galaxy.root+"history/set_as_current?id="+c),d.save({content:this.id,source:"library"},{success:function(){Galaxy.modal.hide(),a.success("Dataset imported. Click this to start analyzing it.","",{onclick:function(){window.location="/"}})},error:function(b,c){"undefined"!=typeof c.responseJSON?a.error("Dataset not imported. "+c.responseJSON.err_msg):a.error("An error occured. Dataset not imported. Please try again.")}})},shareDataset:function(){a.info("Feature coming soon.")},goBack:function(){Galaxy.libraries.library_router.back()},showPermissions:function(b){this.options=_.extend(this.options,b),$(".tooltip").remove(),void 0!==this.options.fetched_permissions&&(0===this.options.fetched_permissions.access_dataset_roles.length?this.model.set({is_unrestricted:!0}):this.model.set({is_unrestricted:!1}));var c=!1;Galaxy.user&&(c=Galaxy.user.isAdmin());var d=this.templateDatasetPermissions();this.$el.html(d({item:this.model,is_admin:c}));var e=this;$.get(Galaxy.root+"api/libraries/datasets/"+e.id+"/permissions?scope=current").done(function(a){e.prepareSelectBoxes({fetched_permissions:a,is_admin:c})}).fail(function(){a.error("An error occurred while attempting to fetch dataset permissions.")}),$("#center [data-toggle]").tooltip(),$("#center").css("overflow","auto")},_serializeRoles:function(a){for(var b=[],c=0;c<a.length;c++)b.push(a[c][1]+":"+a[c][0]);return b},prepareSelectBoxes:function(b){this.options=_.extend(this.options,b);var c=this.options.fetched_permissions,e=this.options.is_admin,f=this,g=[],h=[],i=[];if(g=this._serializeRoles(c.access_dataset_roles),h=this._serializeRoles(c.modify_item_roles),i=this._serializeRoles(c.manage_dataset_roles),e){var j={minimumInputLength:0,css:"access_perm",multiple:!0,placeholder:"Click to select a role",container:f.$el.find("#access_perm"),ajax:{url:Galaxy.root+"api/libraries/datasets/"+f.id+"/permissions?scope=available",dataType:"json",quietMillis:100,data:function(a,b){return{q:a,page_limit:10,page:b}},results:function(a,b){var c=10*b<a.total;return{results:a.roles,more:c}}},formatResult:function(a){return a.name+" type: "+a.type},formatSelection:function(a){return a.name},initSelection:function(a,b){var c=[];$(a.val().split(",")).each(function(){var a=this.split(":");c.push({id:a[0],name:a[1]})}),b(c)},initialData:g.join(","),dropdownCssClass:"bigdrop"},k={minimumInputLength:0,css:"modify_perm",multiple:!0,placeholder:"Click to select a role",container:f.$el.find("#modify_perm"),ajax:{url:Galaxy.root+"api/libraries/datasets/"+f.id+"/permissions?scope=available",dataType:"json",quietMillis:100,data:function(a,b){return{q:a,page_limit:10,page:b}},results:function(a,b){var c=10*b<a.total;return{results:a.roles,more:c}}},formatResult:function(a){return a.name+" type: "+a.type},formatSelection:function(a){return a.name},initSelection:function(a,b){var c=[];$(a.val().split(",")).each(function(){var a=this.split(":");c.push({id:a[0],name:a[1]})}),b(c)},initialData:h.join(","),dropdownCssClass:"bigdrop"},l={minimumInputLength:0,css:"manage_perm",multiple:!0,placeholder:"Click to select a role",container:f.$el.find("#manage_perm"),ajax:{url:Galaxy.root+"api/libraries/datasets/"+f.id+"/permissions?scope=available",dataType:"json",quietMillis:100,data:function(a,b){return{q:a,page_limit:10,page:b}},results:function(a,b){var c=10*b<a.total;return{results:a.roles,more:c}}},formatResult:function(a){return a.name+" type: "+a.type},formatSelection:function(a){return a.name},initSelection:function(a,b){var c=[];$(a.val().split(",")).each(function(){var a=this.split(":");c.push({id:a[0],name:a[1]})}),b(c)},initialData:i.join(","),dropdownCssClass:"bigdrop"};f.accessSelectObject=new d.View(j),f.modifySelectObject=new d.View(k),f.manageSelectObject=new d.View(l)}else{var m=f.templateAccessSelect();$.get(Galaxy.root+"api/libraries/datasets/"+f.id+"/permissions?scope=available",function(a){$(".access_perm").html(m({options:a.roles})),f.accessSelectObject=$("#access_select").select2()}).fail(function(){a.error("An error occurred while attempting to fetch dataset permissions.")})}},comingSoon:function(){a.warning("Feature coming soon.")},copyToClipboard:function(){var a=Backbone.history.location.href;a.lastIndexOf("/permissions")!==-1&&(a=a.substr(0,a.lastIndexOf("/permissions"))),window.prompt("Copy to clipboard: Ctrl+C, Enter",a)},makeDatasetPrivate:function(){var b=this;$.post(Galaxy.root+"api/libraries/datasets/"+b.id+"/permissions?action=make_private").done(function(c){b.model.set({is_unrestricted:!1}),b.showPermissions({fetched_permissions:c}),a.success("The dataset is now private to you.")}).fail(function(){a.error("An error occurred while attempting to make dataset private.")})},removeDatasetRestrictions:function(){var b=this;$.post(Galaxy.root+"api/libraries/datasets/"+b.id+"/permissions?action=remove_restrictions").done(function(c){b.model.set({is_unrestricted:!0}),b.showPermissions({fetched_permissions:c}),a.success("Access to this dataset is now unrestricted.")}).fail(function(){a.error("An error occurred while attempting to make dataset unrestricted.")})},_extractIds:function(a){ids_list=[];for(var b=a.length-1;b>=0;b--)ids_list.push(a[b].id);return ids_list},savePermissions:function(b){var c=this,d=this._extractIds(this.accessSelectObject.$el.select2("data")),e=this._extractIds(this.manageSelectObject.$el.select2("data")),f=this._extractIds(this.modifySelectObject.$el.select2("data"));$.post(Galaxy.root+"api/libraries/datasets/"+c.id+"/permissions?action=set_permissions",{"access_ids[]":d,"manage_ids[]":e,"modify_ids[]":f}).done(function(b){c.showPermissions({fetched_permissions:b}),a.success("Permissions saved.")}).fail(function(){a.error("An error occurred while attempting to set dataset permissions.")})},fetchExtAndGenomes:function(){var a=this;c.get({url:Galaxy.root+"api/datatypes?extension_only=False",success:function(b){for(key in b)a.list_extensions.push({id:b[key].extension,text:b[key].extension,description:b[key].description,description_url:b[key].description_url});a.list_extensions.sort(function(a,b){return a.id>b.id?1:a.id<b.id?-1:0}),a.list_extensions.unshift(a.auto)}}),c.get({url:Galaxy.root+"api/genomes",success:function(b){for(key in b)a.list_genomes.push({id:b[key][1],text:b[key][0]});a.list_genomes.sort(function(a,b){return a.id>b.id?1:a.id<b.id?-1:0})}})},renderSelectBoxes:function(a){var b="?",c="auto";"undefined"!=typeof a&&("undefined"!=typeof a.genome_build&&(b=a.genome_build),"undefined"!=typeof a.file_ext&&(c=a.file_ext));var e=this;this.select_genome=new d.View({css:"dataset-genome-select",data:e.list_genomes,container:e.$el.find("#dataset_genome_select"),value:b}),this.select_extension=new d.View({css:"dataset-extension-select",data:e.list_extensions,container:e.$el.find("#dataset_extension_select"),value:c})},templateDataset:function(){return _.template(['<div class="library_style_container">','<div id="library_toolbar">','<button data-toggle="tooltip" data-placement="top" title="Download dataset" class="btn btn-default toolbtn-download-dataset primary-button toolbar-item" type="button">','<span class="fa fa-download"></span>',"&nbsp;Download","</button>",'<button data-toggle="tooltip" data-placement="top" title="Import dataset into history" class="btn btn-default toolbtn-import-dataset primary-button toolbar-item" type="button">','<span class="fa fa-book"></span>',"&nbsp;to History","</button>",'<% if (item.get("can_user_modify")) { %>','<button data-toggle="tooltip" data-placement="top" title="Modify library item" class="btn btn-default toolbtn_modify_dataset primary-button toolbar-item" type="button">','<span class="fa fa-pencil"></span>',"&nbsp;Modify","</button>","<% } %>",'<% if (item.get("can_user_manage")) { %>','<a href="#folders/<%- item.get("folder_id") %>/datasets/<%- item.id %>/permissions">','<button data-toggle="tooltip" data-placement="top" title="Manage permissions" class="btn btn-default toolbtn_change_permissions primary-button toolbar-item" type="button">','<span class="fa fa-group"></span>',"&nbsp;Permissions","</button>","</a>","<% } %>","</div>",'<ol class="breadcrumb">','<li><a title="Return to the list of libraries" href="#">Libraries</a></li>','<% _.each(item.get("full_path"), function(path_item) { %>',"<% if (path_item[0] != item.id) { %>",'<li><a title="Return to this folder" href="#/folders/<%- path_item[0] %>"><%- path_item[1] %></a> </li> ',"<% } else { %>",'<li class="active"><span title="You are here"><%- path_item[1] %></span></li>',"<% } %>","<% }); %>","</ol>",'<% if (item.get("is_unrestricted")) { %>','<div class="alert alert-info">',"This dataset is unrestricted so everybody can access it. Just share the URL of this page. ",'<button data-toggle="tooltip" data-placement="top" title="Copy to clipboard" class="btn btn-default btn-copy-link-to-clipboard primary-button" type="button">','<span class="fa fa-clipboard"></span>',"&nbsp;To Clipboard","</button> ","</div>","<% } %>",'<div class="dataset_table">','<table class="grid table table-striped table-condensed">',"<tr>",'<th class="dataset-first-column" scope="row" id="id_row" data-id="<%= _.escape(item.get("ldda_id")) %>">Name</th>','<td><%= _.escape(item.get("name")) %></td>',"</tr>",'<% if (item.get("file_ext")) { %>',"<tr>",'<th scope="row">Data type</th>','<td><%= _.escape(item.get("file_ext")) %></td>',"</tr>","<% } %>",'<% if (item.get("genome_build")) { %>',"<tr>",'<th scope="row">Genome build</th>','<td><%= _.escape(item.get("genome_build")) %></td>',"</tr>","<% } %>",'<% if (item.get("file_size")) { %>',"<tr>",'<th scope="row">Size</th>','<td><%= _.escape(item.get("file_size")) %></td>',"</tr>","<% } %>",'<% if (item.get("date_uploaded")) { %>',"<tr>",'<th scope="row">Date uploaded (UTC)</th>','<td><%= _.escape(item.get("date_uploaded")) %></td>',"</tr>","<% } %>",'<% if (item.get("uploaded_by")) { %>',"<tr>",'<th scope="row">Uploaded by</th>','<td><%= _.escape(item.get("uploaded_by")) %></td>',"</tr>","<% } %>",'<% if (item.get("metadata_data_lines")) { %>',"<tr>",'<th scope="row">Data Lines</th>','<td scope="row"><%= _.escape(item.get("metadata_data_lines")) %></td>',"</tr>","<% } %>",'<% if (item.get("metadata_comment_lines")) { %>',"<tr>",'<th scope="row">Comment Lines</th>','<td scope="row"><%= _.escape(item.get("metadata_comment_lines")) %></td>',"</tr>","<% } %>",'<% if (item.get("metadata_columns")) { %>',"<tr>",'<th scope="row">Number of Columns</th>','<td scope="row"><%= _.escape(item.get("metadata_columns")) %></td>',"</tr>","<% } %>",'<% if (item.get("metadata_column_types")) { %>',"<tr>",'<th scope="row">Column Types</th>','<td scope="row"><%= _.escape(item.get("metadata_column_types")) %></td>',"</tr>","<% } %>",'<% if (item.get("message")) { %>',"<tr>",'<th scope="row">Message</th>','<td scope="row"><%= _.escape(item.get("message")) %></td>',"</tr>","<% } %>",'<% if (item.get("misc_blurb")) { %>',"<tr>",'<th scope="row">Miscellaneous blurb</th>','<td scope="row"><%= _.escape(item.get("misc_blurb")) %></td>',"</tr>","<% } %>",'<% if (item.get("misc_info")) { %>',"<tr>",'<th scope="row">Miscellaneous information</th>','<td scope="row"><%= _.escape(item.get("misc_info")) %></td>',"</tr>","<% } %>","</table>","<div>",'<pre class="peek">',"</pre>","</div>",'<% if (item.get("has_versions")) { %>',"<div>","<h3>Expired versions:</h3>","<ul>",'<% _.each(item.get("expired_versions"), function(version) { %>','<li><a title="See details of this version" href="#folders/<%- item.get("folder_id") %>/datasets/<%- item.id %>/versions/<%- version[0] %>"><%- version[1] %></a></li>',"<% }) %>","<ul>","</div>","<% } %>","</div>","</div>"].join(""))},templateVersion:function(){return _.template(['<div class="library_style_container">','<div id="library_toolbar">','<a href="#folders/<%- item.get("folder_id") %>/datasets/<%- item.id %>">','<button data-toggle="tooltip" data-placement="top" title="Go to latest dataset" class="btn btn-default primary-button toolbar-item" type="button">','<span class="fa fa-caret-left fa-lg"></span>',"&nbsp;Latest dataset","</button>","<a>","</div>",'<ol class="breadcrumb">','<li><a title="Return to the list of libraries" href="#">Libraries</a></li>','<% _.each(item.get("full_path"), function(path_item) { %>',"<% if (path_item[0] != item.id) { %>",'<li><a title="Return to this folder" href="#/folders/<%- path_item[0] %>"><%- path_item[1] %></a> </li> ',"<% } else { %>",'<li class="active"><span title="You are here"><%- path_item[1] %></span></li>',"<% } %>","<% }); %>","</ol>",'<div class="alert alert-warning">This is an expired version of the library dataset: <%= _.escape(item.get("name")) %></div>','<div class="dataset_table">','<table class="grid table table-striped table-condensed">',"<tr>",'<th scope="row" id="id_row" data-id="<%= _.escape(ldda.id) %>">Name</th>','<td><%= _.escape(ldda.get("name")) %></td>',"</tr>",'<% if (ldda.get("file_ext")) { %>',"<tr>",'<th scope="row">Data type</th>','<td><%= _.escape(ldda.get("file_ext")) %></td>',"</tr>","<% } %>",'<% if (ldda.get("genome_build")) { %>',"<tr>",'<th scope="row">Genome build</th>','<td><%= _.escape(ldda.get("genome_build")) %></td>',"</tr>","<% } %>",'<% if (ldda.get("file_size")) { %>',"<tr>",'<th scope="row">Size</th>','<td><%= _.escape(ldda.get("file_size")) %></td>',"</tr>","<% } %>",'<% if (ldda.get("date_uploaded")) { %>',"<tr>",'<th scope="row">Date uploaded (UTC)</th>','<td><%= _.escape(ldda.get("date_uploaded")) %></td>',"</tr>","<% } %>",'<% if (ldda.get("uploaded_by")) { %>',"<tr>",'<th scope="row">Uploaded by</th>','<td><%= _.escape(ldda.get("uploaded_by")) %></td>',"</tr>","<% } %>",'<% if (ldda.get("metadata_data_lines")) { %>',"<tr>",'<th scope="row">Data Lines</th>','<td scope="row"><%= _.escape(ldda.get("metadata_data_lines")) %></td>',"</tr>","<% } %>",'<% if (ldda.get("metadata_comment_lines")) { %>',"<tr>",'<th scope="row">Comment Lines</th>','<td scope="row"><%= _.escape(ldda.get("metadata_comment_lines")) %></td>',"</tr>","<% } %>",'<% if (ldda.get("metadata_columns")) { %>',"<tr>",'<th scope="row">Number of Columns</th>','<td scope="row"><%= _.escape(ldda.get("metadata_columns")) %></td>',"</tr>","<% } %>",'<% if (ldda.get("metadata_column_types")) { %>',"<tr>",'<th scope="row">Column Types</th>','<td scope="row"><%= _.escape(ldda.get("metadata_column_types")) %></td>',"</tr>","<% } %>",'<% if (ldda.get("message")) { %>',"<tr>",'<th scope="row">Message</th>','<td scope="row"><%= _.escape(ldda.get("message")) %></td>',"</tr>","<% } %>",'<% if (ldda.get("misc_blurb")) { %>',"<tr>",'<th scope="row">Miscellaneous blurb</th>','<td scope="row"><%= _.escape(ldda.get("misc_blurb")) %></td>',"</tr>","<% } %>",'<% if (ldda.get("misc_info")) { %>',"<tr>",'<th scope="row">Miscellaneous information</th>','<td scope="row"><%= _.escape(ldda.get("misc_info")) %></td>',"</tr>","<% } %>","</table>","<div>",'<pre class="peek">',"</pre>","</div>","</div>","</div>"].join(""))},templateModifyDataset:function(){return _.template(['<div class="library_style_container">','<div id="library_toolbar">','<button data-toggle="tooltip" data-placement="top" title="Cancel modifications" class="btn btn-default toolbtn_cancel_modifications primary-button toolbar-item" type="button">','<span class="fa fa-times"></span>',"&nbsp;Cancel","</button>",'<button data-toggle="tooltip" data-placement="top" title="Save modifications" class="btn btn-default toolbtn_save_modifications primary-button toolbar-item" type="button">','<span class="fa fa-floppy-o"></span>',"&nbsp;Save","</button>","</div>",'<ol class="breadcrumb">','<li><a title="Return to the list of libraries" href="#">Libraries</a></li>','<% _.each(item.get("full_path"), function(path_item) { %>',"<% if (path_item[0] != item.id) { %>",'<li><a title="Return to this folder" href="#/folders/<%- path_item[0] %>"><%- path_item[1] %></a> </li> ',"<% } else { %>",'<li class="active"><span title="You are here"><%- path_item[1] %></span></li>',"<% } %>","<% }); %>","</ol>",'<div class="dataset_table">','<p>For full editing options please import the dataset to history and use "Edit attributes" on it.</p>','<table class="grid table table-striped table-condensed">',"<tr>",'<th class="dataset-first-column" scope="row" id="id_row" data-id="<%= _.escape(item.get("ldda_id")) %>">Name</th>','<td><input class="input_dataset_name form-control" type="text" placeholder="name" value="<%= _.escape(item.get("name")) %>"></td>',"</tr>","<tr>",'<th scope="row">Data type</th>',"<td>",'<span id="dataset_extension_select" class="dataset-extension-select" />',"</td>","</tr>","<tr>",'<th scope="row">Genome build</th>',"<td>",'<span id="dataset_genome_select" class="dataset-genome-select" />',"</td>","</tr>","<tr>",'<th scope="row">Size</th>','<td><%= _.escape(item.get("file_size")) %></td>',"</tr>","<tr>",'<th scope="row">Date uploaded (UTC)</th>','<td><%= _.escape(item.get("date_uploaded")) %></td>',"</tr>","<tr>",'<th scope="row">Uploaded by</th>','<td><%= _.escape(item.get("uploaded_by")) %></td>',"</tr>",'<tr scope="row">','<th scope="row">Data Lines</th>','<td scope="row"><%= _.escape(item.get("metadata_data_lines")) %></td>',"</tr>",'<th scope="row">Comment Lines</th>','<% if (item.get("metadata_comment_lines") === "") { %>','<td scope="row"><%= _.escape(item.get("metadata_comment_lines")) %></td>',"<% } else { %>",'<td scope="row">unknown</td>',"<% } %>","</tr>","<tr>",'<th scope="row">Number of Columns</th>','<td scope="row"><%= _.escape(item.get("metadata_columns")) %></td>',"</tr>","<tr>",'<th scope="row">Column Types</th>','<td scope="row"><%= _.escape(item.get("metadata_column_types")) %></td>',"</tr>","<tr>",'<th scope="row">Message</th>','<td scope="row"><%= _.escape(item.get("message")) %></td>',"</tr>","<tr>",'<th scope="row">Miscellaneous information</th>','<td scope="row"><%= _.escape(item.get("misc_info")) %></td>',"</tr>","<tr>",'<th scope="row">Miscellaneous blurb</th>','<td scope="row"><%= _.escape(item.get("misc_blurb")) %></td>',"</tr>","</table>","<div>",'<pre class="peek">',"</pre>","</div>","</div>","</div>"].join(""))},templateDatasetPermissions:function(){return _.template(['<div class="library_style_container">','<div id="library_toolbar">','<a href="#folders/<%- item.get("folder_id") %>">','<button data-toggle="tooltip" data-placement="top" title="Go back to containing folder" class="btn btn-default primary-button toolbar-item" type="button">','<span class="fa fa-folder-open-o"></span>',"&nbsp;Containing Folder","</button>","</a>",'<a href="#folders/<%- item.get("folder_id") %>/datasets/<%- item.id %>">','<button data-toggle="tooltip" data-placement="top" title="Go back to dataset" class="btn btn-default primary-button toolbar-item" type="button">','<span class="fa fa-file-o"></span>',"&nbsp;Dataset Details","</button>","<a>","</div>",'<ol class="breadcrumb">','<li><a title="Return to the list of libraries" href="#">Libraries</a></li>','<% _.each(item.get("full_path"), function(path_item) { %>',"<% if (path_item[0] != item.id) { %>",'<li><a title="Return to this folder" href="#/folders/<%- path_item[0] %>"><%- path_item[1] %></a> </li> ',"<% } else { %>",'<li class="active"><span title="You are here"><%- path_item[1] %></span></li>',"<% } %>","<% }); %>","</ol>",'<h1>Dataset: <%= _.escape(item.get("name")) %></h1>','<div class="alert alert-warning">',"<% if (is_admin) { %>","You are logged in as an <strong>administrator</strong> therefore you can manage any dataset on this Galaxy instance. Please make sure you understand the consequences.","<% } else { %>","You can assign any number of roles to any of the following permission types. However please read carefully the implications of such actions.","<% } %>","</div>",'<div class="dataset_table">',"<h2>Library-related permissions</h2>","<h4>Roles that can modify the library item</h4>",'<div id="modify_perm" class="modify_perm roles-selection"></div>','<div class="alert alert-info roles-selection">User with <strong>any</strong> of these roles can modify name, metadata, and other information about this library item.</div>',"<hr/>","<h2>Dataset-related permissions</h2>",'<div class="alert alert-warning">Changes made below will affect <strong>every</strong> library item that was created from this dataset and also every history this dataset is part of.</div>','<% if (!item.get("is_unrestricted")) { %>',"<p>You can remove all access restrictions on this dataset. ",'<button data-toggle="tooltip" data-placement="top" title="Everybody will be able to access the dataset." class="btn btn-default btn-remove-restrictions primary-button" type="button">','<span class="fa fa-globe"></span>',"&nbsp;Remove restrictions","</button>","</p>","<% } else { %>","This dataset is unrestricted so everybody can access it. Just share the URL of this page.",'<button data-toggle="tooltip" data-placement="top" title="Copy to clipboard" class="btn btn-default btn-copy-link-to-clipboard primary-button" type="button">','<span class="fa fa-clipboard"></span>',"&nbsp;To Clipboard","</button>","<p>You can make this dataset private to you. ",'<button data-toggle="tooltip" data-placement="top" title="Only you will be able to access the dataset." class="btn btn-default btn-make-private primary-button" type="button">','<span class="fa fa-key"></span>',"&nbsp;Make Private","</button>","</p>","<% } %>","<h4>Roles that can access the dataset</h4>",'<div id="access_perm" class="access_perm roles-selection"></div>','<div class="alert alert-info roles-selection">',"User has to have <strong>all these roles</strong> in order to access this dataset."," Users without access permission <strong>cannot</strong> have other permissions on this dataset."," If there are no access roles set on the dataset it is considered <strong>unrestricted</strong>.","</div>","<h4>Roles that can manage permissions on the dataset</h4>",'<div id="manage_perm" class="manage_perm roles-selection"></div>','<div class="alert alert-info roles-selection">',"User with <strong>any</strong> of these roles can manage permissions of this dataset. If you remove yourself you will loose the ability manage this dataset unless you are an admin.","</div>",'<button data-toggle="tooltip" data-placement="top" title="Save modifications made on this page" class="btn btn-default toolbtn_save_permissions primary-button" type="button">','<span class="fa fa-floppy-o"></span>',"&nbsp;Save","</button>","</div>","</div>"].join(""))},templateBulkImportInModal:function(){return _.template(["<div>",'<div class="library-modal-item">',"Select history: ",'<select id="dataset_import_single" name="dataset_import_single" style="width:50%; margin-bottom: 1em; " autofocus>',"<% _.each(histories, function(history) { %>",'<option value="<%= _.escape(history.get("id")) %>"><%= _.escape(history.get("name")) %></option>',"<% }); %>","</select>","</div>",'<div class="library-modal-item">',"or create new: ",'<input type="text" name="history_name" value="" placeholder="name of the new history" style="width:50%;">',"</input>","</div>","</div>"].join(""))},templateAccessSelect:function(){return _.template(['<select id="access_select" multiple>',"<% _.each(options, function(option) { %>",'<option value="<%- option.name %>"><%- option.name %></option>',"<% }); %>","</select>"].join(""))}});return{LibraryDatasetView:e}});
//# sourceMappingURL=../../../maps/mvc/library/library-dataset-view.js.map