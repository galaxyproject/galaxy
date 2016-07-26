define(["mvc/ui/ui-modal","utils/localization"],function(a,b){"use strict";var c={defaultName:_.template("Copy of '<%- name %>'"),title:_.template(b("Copying history")+' "<%- name %>"'),submitLabel:b("Copy"),errorMessage:b("History could not be copied"),progressive:b("Copying history"),activeLabel:b("Copy only the active, non-deleted datasets"),allLabel:b("Copy all datasets including deleted ones"),anonWarning:b("As an anonymous user, unless you login or register, you will lose your current history ")+b("after copying this history. "),_template:_.template(["<% if( isAnon ){ %>",'<div class="warningmessage">',"<%- anonWarning %>",b("You can"),' <a href="/user/login">',b("login here"),"</a> ",b("or")," ",' <a href="/user/create">',b("register here"),"</a>.","</div>","<% } %>","<form>",'<label for="copy-modal-title">',b("Enter a title for the new history"),":","</label><br />",'<input id="copy-modal-title" class="form-control" style="width: 100%" value="<%= name %>" />','<p class="invalid-title bg-danger" style="color: red; margin: 8px 0px 8px 0px; display: none">',b("Please enter a valid history title"),"</p>","<% if( allowAll ){ %>","<br />","<p>",b("Choose which datasets from the original history to include:"),"</p>",'<input name="copy-what" type="radio" id="copy-non-deleted" value="copy-non-deleted" ','<% if( copyWhat === "copy-non-deleted" ){ print( "checked" ); } %>/>','<label for="copy-non-deleted"> <%- activeLabel %></label>',"<br />",'<input name="copy-what" type="radio" id="copy-all" value="copy-all" ','<% if( copyWhat === "copy-all" ){ print( "checked" ); } %>/>','<label for="copy-all"> <%- allLabel %></label>',"<% } %>","</form>"].join("")),_showAjaxIndicator:function(){var a='<p><span class="fa fa-spinner fa-spin"></span> '+this.progressive+"...</p>";this.modal.$(".modal-body").empty().append(a).css({"margin-top":"8px"})},dialog:function(a,c,d){function e(){var d=a.$("#copy-modal-title").val();if(!d)return void a.$(".invalid-title").show();var e="copy-all"===a.$('input[name="copy-what"]:checked').val();a.$("button").prop("disabled",!0),f._showAjaxIndicator(),c.copy(!0,d,e).done(function(a){g.resolve(a)}).fail(function(){alert([f.errorMessage,b("Please contact a Galaxy administrator")].join(". ")),g.rejectWith(g,arguments)}).always(function(){l&&a.hide()})}d=d||{};var f=this,g=jQuery.Deferred(),h=d.nameFn||this.defaultName,i=h({name:c.get("name")}),j=d.allDatasets?"copy-all":"copy-non-deleted",k=!!_.isUndefined(d.allowAll)||d.allowAll,l=!!_.isUndefined(d.autoClose)||d.autoClose;this.modal=a;var m=d.closing_callback;return a.show(_.extend(d,{title:this.title({name:c.get("name")}),body:$(f._template({name:i,isAnon:Galaxy.user.isAnonymous(),allowAll:k,copyWhat:j,activeLabel:this.activeLabel,allLabel:this.allLabel,anonWarning:this.anonWarning})),buttons:_.object([[b("Cancel"),function(){a.hide()}],[this.submitLabel,e]]),height:"auto",closing_events:!0,closing_callback:function(a){a&&g.reject({cancelled:!0}),m&&m(a)}})),a.$("#copy-modal-title").focus().select(),a.$("#copy-modal-title").on("keydown",function(a){13===a.keyCode&&(a.preventDefault(),e())}),g}},d=_.extend({},c,{defaultName:_.template("imported: <%- name %>"),title:_.template(b("Importing history")+' "<%- name %>"'),submitLabel:b("Import"),errorMessage:b("History could not be imported"),progressive:b("Importing history"),activeLabel:b("Import only the active, non-deleted datasets"),allLabel:b("Import all datasets including deleted ones"),anonWarning:b("As an anonymous user, unless you login or register, you will lose your current history ")+b("after importing this history. ")}),e=function(b,e){e=e||{};var f=window.parent.Galaxy.modal||new a.View({});return e.useImport?d.dialog(f,b,e):c.dialog(f,b,e)};return e});
//# sourceMappingURL=../../../maps/mvc/history/copy-dialog.js.map