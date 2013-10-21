/** Hack div to clear re-enclose float'd elements above it in the parent div
 */
Handlebars.registerPartial( 'clearFloatDiv', function( options ){
    return '<div class="clear"></div>';
});
/** Renders a warning in a (mostly css) highlighted, iconned warning box
 */
Handlebars.registerHelper( 'warningmessagesmall', function( options ){
    return '<div class="warningmessagesmall"><strong>' + options.fn( this ) + '</strong></div>'
});
/** Calls _l (from base-mvc.js) to localize strings (if poosible)
 *  This helper is specifically for localization within templates
 */
Handlebars.registerHelper( 'local', function( options ){
    return _l( options.fn( this ) );
});(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-hda-annotationArea'] = template(function (Handlebars,depth0,helpers,partials,data) {
  this.compilerInfo = [4,'>= 1.0.0'];
helpers = this.merge(helpers, Handlebars.helpers); data = data || {};
  var buffer = "", stack1, options, functionType="function", escapeExpression=this.escapeExpression, self=this, blockHelperMissing=helpers.blockHelperMissing;

function program1(depth0,data) {
  
  
  return "Annotation";
  }

function program3(depth0,data) {
  
  
  return "Edit dataset annotation";
  }

  buffer += "\n<div id=\"";
  if (stack1 = helpers.id) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.id; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "-annotation-area\" class=\"annotation-area\" style=\"display: none;\">\n    <strong>";
  options = {hash:{},inverse:self.noop,fn:self.program(1, program1, data),data:data};
  if (stack1 = helpers.local) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += ":</strong>\n    <div id=\"";
  if (stack1 = helpers.id) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.id; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "-anotation-elt\" class=\"annotation-elt editable-text\"\n         style=\"margin: 1px 0px 1px 0px\" title=\"";
  options = {hash:{},inverse:self.noop,fn:self.program(3, program3, data),data:data};
  if (stack1 = helpers.local) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\">\n    </div>\n</div>";
  return buffer;
  });
})();(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-hda-displayApps'] = template(function (Handlebars,depth0,helpers,partials,data) {
  this.compilerInfo = [4,'>= 1.0.0'];
helpers = this.merge(helpers, Handlebars.helpers); data = data || {};
  var stack1, functionType="function", escapeExpression=this.escapeExpression, self=this, blockHelperMissing=helpers.blockHelperMissing;

function program1(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n    ";
  if (stack1 = helpers.label) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.label; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "\n    ";
  stack1 = helpers.each.call(depth0, depth0.links, {hash:{},inverse:self.noop,fn:self.program(2, program2, data),data:data});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n    <br />\n";
  return buffer;
  }
function program2(depth0,data) {
  
  var buffer = "", stack1, options;
  buffer += "\n        <a target=\"";
  if (stack1 = helpers.target) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.target; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "\" href=\"";
  if (stack1 = helpers.href) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.href; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "\">";
  options = {hash:{},inverse:self.noop,fn:self.program(3, program3, data),data:data};
  if (stack1 = helpers.local) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "</a>\n    ";
  return buffer;
  }
function program3(depth0,data) {
  
  var stack1;
  if (stack1 = helpers.text) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.text; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  return escapeExpression(stack1);
  }

  stack1 = helpers.each.call(depth0, depth0.displayApps, {hash:{},inverse:self.noop,fn:self.program(1, program1, data),data:data});
  if(stack1 || stack1 === 0) { return stack1; }
  else { return ''; }
  });
})();(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-hda-downloadLinks'] = template(function (Handlebars,depth0,helpers,partials,data) {
  this.compilerInfo = [4,'>= 1.0.0'];
helpers = this.merge(helpers, Handlebars.helpers); data = data || {};
  var stack1, stack2, functionType="function", escapeExpression=this.escapeExpression, self=this, blockHelperMissing=helpers.blockHelperMissing;

function program1(depth0,data) {
  
  var buffer = "", stack1, stack2, options;
  buffer += "\n<div popupmenu=\"dataset-";
  if (stack1 = helpers.id) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.id; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "-popup\">\n    <a class=\"action-button\" href=\""
    + escapeExpression(((stack1 = ((stack1 = depth0.urls),stack1 == null || stack1 === false ? stack1 : stack1.download)),typeof stack1 === functionType ? stack1.apply(depth0) : stack1))
    + "\">";
  options = {hash:{},inverse:self.noop,fn:self.program(2, program2, data),data:data};
  if (stack2 = helpers.local) { stack2 = stack2.call(depth0, options); }
  else { stack2 = depth0.local; stack2 = typeof stack2 === functionType ? stack2.apply(depth0) : stack2; }
  if (!helpers.local) { stack2 = blockHelperMissing.call(depth0, stack2, options); }
  if(stack2 || stack2 === 0) { buffer += stack2; }
  buffer += "</a>\n    <a>";
  options = {hash:{},inverse:self.noop,fn:self.program(4, program4, data),data:data};
  if (stack2 = helpers.local) { stack2 = stack2.call(depth0, options); }
  else { stack2 = depth0.local; stack2 = typeof stack2 === functionType ? stack2.apply(depth0) : stack2; }
  if (!helpers.local) { stack2 = blockHelperMissing.call(depth0, stack2, options); }
  if(stack2 || stack2 === 0) { buffer += stack2; }
  buffer += "</a>\n    ";
  stack2 = helpers.each.call(depth0, ((stack1 = depth0.urls),stack1 == null || stack1 === false ? stack1 : stack1.meta_download), {hash:{},inverse:self.noop,fn:self.program(6, program6, data),data:data});
  if(stack2 || stack2 === 0) { buffer += stack2; }
  buffer += "\n</div>\n<div style=\"float:left;\" class=\"menubutton split popup\" id=\"dataset-";
  if (stack2 = helpers.id) { stack2 = stack2.call(depth0, {hash:{},data:data}); }
  else { stack2 = depth0.id; stack2 = typeof stack2 === functionType ? stack2.apply(depth0) : stack2; }
  buffer += escapeExpression(stack2)
    + "-popup\">\n    <a href=\""
    + escapeExpression(((stack1 = ((stack1 = depth0.urls),stack1 == null || stack1 === false ? stack1 : stack1.download)),typeof stack1 === functionType ? stack1.apply(depth0) : stack1))
    + "\" title=\"";
  options = {hash:{},inverse:self.noop,fn:self.program(7, program7, data),data:data};
  if (stack2 = helpers.local) { stack2 = stack2.call(depth0, options); }
  else { stack2 = depth0.local; stack2 = typeof stack2 === functionType ? stack2.apply(depth0) : stack2; }
  if (!helpers.local) { stack2 = blockHelperMissing.call(depth0, stack2, options); }
  if(stack2 || stack2 === 0) { buffer += stack2; }
  buffer += "\" class=\"icon-button disk\"></a>\n</div>\n";
  return buffer;
  }
function program2(depth0,data) {
  
  
  return "Download Dataset";
  }

function program4(depth0,data) {
  
  
  return "Additional Files";
  }

function program6(depth0,data) {
  
  var buffer = "", stack1, options;
  buffer += "\n    <a class=\"action-button\" href=\"";
  if (stack1 = helpers.url) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.url; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "\">";
  options = {hash:{},inverse:self.noop,fn:self.program(7, program7, data),data:data};
  if (stack1 = helpers.local) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += " ";
  if (stack1 = helpers.file_type) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.file_type; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "</a>\n    ";
  return buffer;
  }
function program7(depth0,data) {
  
  
  return "Download";
  }

function program9(depth0,data) {
  
  var buffer = "", stack1, stack2, options;
  buffer += "\n"
    + "\n<a href=\""
    + escapeExpression(((stack1 = ((stack1 = depth0.urls),stack1 == null || stack1 === false ? stack1 : stack1.download)),typeof stack1 === functionType ? stack1.apply(depth0) : stack1))
    + "\" title=\"";
  options = {hash:{},inverse:self.noop,fn:self.program(7, program7, data),data:data};
  if (stack2 = helpers.local) { stack2 = stack2.call(depth0, options); }
  else { stack2 = depth0.local; stack2 = typeof stack2 === functionType ? stack2.apply(depth0) : stack2; }
  if (!helpers.local) { stack2 = blockHelperMissing.call(depth0, stack2, options); }
  if(stack2 || stack2 === 0) { buffer += stack2; }
  buffer += "\" class=\"icon-button disk\"></a>\n";
  return buffer;
  }

  stack2 = helpers['if'].call(depth0, ((stack1 = depth0.urls),stack1 == null || stack1 === false ? stack1 : stack1.meta_download), {hash:{},inverse:self.program(9, program9, data),fn:self.program(1, program1, data),data:data});
  if(stack2 || stack2 === 0) { return stack2; }
  else { return ''; }
  });
})();(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-hda-failedMetadata'] = template(function (Handlebars,depth0,helpers,partials,data) {
  this.compilerInfo = [4,'>= 1.0.0'];
helpers = this.merge(helpers, Handlebars.helpers); data = data || {};
  var stack1, options, self=this, functionType="function", blockHelperMissing=helpers.blockHelperMissing, escapeExpression=this.escapeExpression;

function program1(depth0,data) {
  
  var buffer = "", stack1, options;
  buffer += "\n";
  options = {hash:{},inverse:self.noop,fn:self.program(2, program2, data),data:data};
  if (stack1 = helpers.local) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\nYou may be able to <a href=\""
    + escapeExpression(((stack1 = ((stack1 = depth0.urls),stack1 == null || stack1 === false ? stack1 : stack1.edit)),typeof stack1 === functionType ? stack1.apply(depth0) : stack1))
    + "\" target=\"galaxy_main\">set it manually or retry auto-detection</a>.\n";
  return buffer;
  }
function program2(depth0,data) {
  
  
  return "An error occurred setting the metadata for this dataset.";
  }

  options = {hash:{},inverse:self.noop,fn:self.program(1, program1, data),data:data};
  if (stack1 = helpers.warningmessagesmall) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.warningmessagesmall; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.warningmessagesmall) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { return stack1; }
  else { return ''; }
  });
})();(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-hda-hdaSummary'] = template(function (Handlebars,depth0,helpers,partials,data) {
  this.compilerInfo = [4,'>= 1.0.0'];
helpers = this.merge(helpers, Handlebars.helpers); data = data || {};
  var buffer = "", stack1, options, functionType="function", escapeExpression=this.escapeExpression, self=this, blockHelperMissing=helpers.blockHelperMissing;

function program1(depth0,data) {
  
  
  return "format: ";
  }

function program3(depth0,data) {
  
  
  return "database: ";
  }

function program5(depth0,data) {
  
  var buffer = "", stack1, stack2;
  buffer += "\n        <a class=\"metadata-dbkey\" href=\""
    + escapeExpression(((stack1 = ((stack1 = depth0.urls),stack1 == null || stack1 === false ? stack1 : stack1.edit)),typeof stack1 === functionType ? stack1.apply(depth0) : stack1))
    + "\" target=\"galaxy_main\">";
  if (stack2 = helpers.metadata_dbkey) { stack2 = stack2.call(depth0, {hash:{},data:data}); }
  else { stack2 = depth0.metadata_dbkey; stack2 = typeof stack2 === functionType ? stack2.apply(depth0) : stack2; }
  buffer += escapeExpression(stack2)
    + "</a>\n    ";
  return buffer;
  }

function program7(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n        <span class=\"metadata-dbkey ";
  if (stack1 = helpers.metadata_dbkey) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.metadata_dbkey; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "\">";
  if (stack1 = helpers.metadata_dbkey) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.metadata_dbkey; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "</span>\n    ";
  return buffer;
  }

function program9(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n<div class=\"hda-info\"> ";
  if (stack1 = helpers.misc_info) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.misc_info; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + " </div>\n";
  return buffer;
  }

  buffer += "<div class=\"hda-summary\">\n    ";
  if (stack1 = helpers.misc_blurb) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.misc_blurb; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "<br />\n    ";
  options = {hash:{},inverse:self.noop,fn:self.program(1, program1, data),data:data};
  if (stack1 = helpers.local) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "<span class=\"";
  if (stack1 = helpers.data_type) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.data_type; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "\">";
  if (stack1 = helpers.data_type) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.data_type; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "</span>,\n    ";
  options = {hash:{},inverse:self.noop,fn:self.program(3, program3, data),data:data};
  if (stack1 = helpers.local) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n    ";
  stack1 = helpers['if'].call(depth0, depth0.dbkey_unknown_and_editable, {hash:{},inverse:self.program(7, program7, data),fn:self.program(5, program5, data),data:data});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n</div>\n";
  stack1 = helpers['if'].call(depth0, depth0.misc_info, {hash:{},inverse:self.noop,fn:self.program(9, program9, data),data:data});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  return buffer;
  });
})();(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-hda-tagArea'] = template(function (Handlebars,depth0,helpers,partials,data) {
  this.compilerInfo = [4,'>= 1.0.0'];
helpers = this.merge(helpers, Handlebars.helpers); data = data || {};
  var buffer = "", stack1, options, self=this, functionType="function", blockHelperMissing=helpers.blockHelperMissing;

function program1(depth0,data) {
  
  
  return "Tags";
  }

  buffer += "\n<div class=\"tag-area\" style=\"display: none;\">\n    <strong>";
  options = {hash:{},inverse:self.noop,fn:self.program(1, program1, data),data:data};
  if (stack1 = helpers.local) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += ":</strong>\n    <div class=\"tag-elt\">\n    </div>\n</div>";
  return buffer;
  });
})();(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-hda-titleLink'] = template(function (Handlebars,depth0,helpers,partials,data) {
  this.compilerInfo = [4,'>= 1.0.0'];
helpers = this.merge(helpers, Handlebars.helpers); data = data || {};
  var buffer = "", stack1, functionType="function", escapeExpression=this.escapeExpression;


  buffer += "<span class=\"historyItemTitle\">";
  if (stack1 = helpers.hid) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.hid; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + ": ";
  if (stack1 = helpers.name) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.name; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "</span>";
  return buffer;
  });
})();(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-hda-warning-messages'] = template(function (Handlebars,depth0,helpers,partials,data) {
  this.compilerInfo = [4,'>= 1.0.0'];
helpers = this.merge(helpers, Handlebars.helpers); data = data || {};
  var buffer = "", stack1, functionType="function", escapeExpression=this.escapeExpression, self=this, blockHelperMissing=helpers.blockHelperMissing;

function program1(depth0,data) {
  
  var buffer = "", stack1, options;
  buffer += "\n<div class=\"errormessagesmall\">\n    ";
  options = {hash:{},inverse:self.noop,fn:self.program(2, program2, data),data:data};
  if (stack1 = helpers.local) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += ":\n    ";
  options = {hash:{},inverse:self.noop,fn:self.program(4, program4, data),data:data};
  if (stack1 = helpers.local) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n</div>\n";
  return buffer;
  }
function program2(depth0,data) {
  
  
  return "There was an error getting the data for this dataset";
  }

function program4(depth0,data) {
  
  var stack1;
  if (stack1 = helpers.error) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.error; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  return escapeExpression(stack1);
  }

function program6(depth0,data) {
  
  var stack1;
  stack1 = helpers.unless.call(depth0, depth0.purged, {hash:{},inverse:self.noop,fn:self.program(7, program7, data),data:data});
  if(stack1 || stack1 === 0) { return stack1; }
  else { return ''; }
  }
function program7(depth0,data) {
  
  var buffer = "", stack1, options;
  buffer += "\n";
  options = {hash:{},inverse:self.noop,fn:self.program(8, program8, data),data:data};
  if (stack1 = helpers.warningmessagesmall) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.warningmessagesmall; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.warningmessagesmall) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n";
  return buffer;
  }
function program8(depth0,data) {
  
  var buffer = "", stack1, stack2, options;
  buffer += "\n    ";
  options = {hash:{},inverse:self.noop,fn:self.program(9, program9, data),data:data};
  if (stack1 = helpers.local) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n    ";
  stack2 = helpers['if'].call(depth0, ((stack1 = depth0.urls),stack1 == null || stack1 === false ? stack1 : stack1.undelete), {hash:{},inverse:self.noop,fn:self.program(11, program11, data),data:data});
  if(stack2 || stack2 === 0) { buffer += stack2; }
  buffer += "\n";
  return buffer;
  }
function program9(depth0,data) {
  
  
  return "This dataset has been deleted.";
  }

function program11(depth0,data) {
  
  var buffer = "", stack1, stack2;
  buffer += "\n        "
    + "\n        Click <a href=\""
    + escapeExpression(((stack1 = ((stack1 = depth0.urls),stack1 == null || stack1 === false ? stack1 : stack1.undelete)),typeof stack1 === functionType ? stack1.apply(depth0) : stack1))
    + "\" class=\"historyItemUndelete\" id=\"historyItemUndeleter-";
  if (stack2 = helpers.id) { stack2 = stack2.call(depth0, {hash:{},data:data}); }
  else { stack2 = depth0.id; stack2 = typeof stack2 === functionType ? stack2.apply(depth0) : stack2; }
  buffer += escapeExpression(stack2)
    + "\"\n                 target=\"galaxy_history\">here</a> to undelete it\n        ";
  stack2 = helpers['if'].call(depth0, ((stack1 = depth0.urls),stack1 == null || stack1 === false ? stack1 : stack1.purge), {hash:{},inverse:self.noop,fn:self.program(12, program12, data),data:data});
  if(stack2 || stack2 === 0) { buffer += stack2; }
  buffer += "\n    ";
  return buffer;
  }
function program12(depth0,data) {
  
  var buffer = "", stack1, stack2;
  buffer += "\n        or <a href=\""
    + escapeExpression(((stack1 = ((stack1 = depth0.urls),stack1 == null || stack1 === false ? stack1 : stack1.purge)),typeof stack1 === functionType ? stack1.apply(depth0) : stack1))
    + "\" class=\"historyItemPurge\" id=\"historyItemPurger-";
  if (stack2 = helpers.id) { stack2 = stack2.call(depth0, {hash:{},data:data}); }
  else { stack2 = depth0.id; stack2 = typeof stack2 === functionType ? stack2.apply(depth0) : stack2; }
  buffer += escapeExpression(stack2)
    + "\"\n           target=\"galaxy_history\">here</a> to immediately remove it from disk\n        ";
  return buffer;
  }

function program14(depth0,data) {
  
  var stack1, options;
  options = {hash:{},inverse:self.noop,fn:self.program(15, program15, data),data:data};
  if (stack1 = helpers.warningmessagesmall) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.warningmessagesmall; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.warningmessagesmall) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { return stack1; }
  else { return ''; }
  }
function program15(depth0,data) {
  
  var buffer = "", stack1, options;
  buffer += "\n    ";
  options = {hash:{},inverse:self.noop,fn:self.program(16, program16, data),data:data};
  if (stack1 = helpers.local) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n";
  return buffer;
  }
function program16(depth0,data) {
  
  
  return "This dataset has been deleted and removed from disk.";
  }

function program18(depth0,data) {
  
  var stack1, options;
  options = {hash:{},inverse:self.noop,fn:self.program(19, program19, data),data:data};
  if (stack1 = helpers.warningmessagesmall) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.warningmessagesmall; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.warningmessagesmall) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { return stack1; }
  else { return ''; }
  }
function program19(depth0,data) {
  
  var buffer = "", stack1, stack2, options;
  buffer += "\n    ";
  options = {hash:{},inverse:self.noop,fn:self.program(20, program20, data),data:data};
  if (stack1 = helpers.local) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n    ";
  stack2 = helpers['if'].call(depth0, ((stack1 = depth0.urls),stack1 == null || stack1 === false ? stack1 : stack1.unhide), {hash:{},inverse:self.noop,fn:self.program(22, program22, data),data:data});
  if(stack2 || stack2 === 0) { buffer += stack2; }
  buffer += "\n";
  return buffer;
  }
function program20(depth0,data) {
  
  
  return "This dataset has been hidden.";
  }

function program22(depth0,data) {
  
  var buffer = "", stack1, stack2;
  buffer += "\n        Click <a href=\""
    + escapeExpression(((stack1 = ((stack1 = depth0.urls),stack1 == null || stack1 === false ? stack1 : stack1.unhide)),typeof stack1 === functionType ? stack1.apply(depth0) : stack1))
    + "\" class=\"historyItemUnhide\" id=\"historyItemUnhider-";
  if (stack2 = helpers.id) { stack2 = stack2.call(depth0, {hash:{},data:data}); }
  else { stack2 = depth0.id; stack2 = typeof stack2 === functionType ? stack2.apply(depth0) : stack2; }
  buffer += escapeExpression(stack2)
    + "\"\n                 target=\"galaxy_history\">here</a> to unhide it\n    ";
  return buffer;
  }

  stack1 = helpers['if'].call(depth0, depth0.error, {hash:{},inverse:self.noop,fn:self.program(1, program1, data),data:data});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n\n";
  stack1 = helpers['if'].call(depth0, depth0.deleted, {hash:{},inverse:self.noop,fn:self.program(6, program6, data),data:data});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n\n";
  stack1 = helpers['if'].call(depth0, depth0.purged, {hash:{},inverse:self.noop,fn:self.program(14, program14, data),data:data});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n\n";
  stack1 = helpers.unless.call(depth0, depth0.visible, {hash:{},inverse:self.noop,fn:self.program(18, program18, data),data:data});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  return buffer;
  });
})();(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-history-historyPanel'] = template(function (Handlebars,depth0,helpers,partials,data) {
  this.compilerInfo = [4,'>= 1.0.0'];
helpers = this.merge(helpers, Handlebars.helpers); data = data || {};
  var buffer = "", stack1, stack2, options, self=this, functionType="function", blockHelperMissing=helpers.blockHelperMissing, escapeExpression=this.escapeExpression;

function program1(depth0,data) {
  
  var buffer = "", stack1, options;
  buffer += "\n            <div id=\"history-name\" class=\"editable-text\"\n                title=\"";
  options = {hash:{},inverse:self.noop,fn:self.program(2, program2, data),data:data};
  if (stack1 = helpers.local) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\">";
  if (stack1 = helpers.name) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.name; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "</div>\n            ";
  return buffer;
  }
function program2(depth0,data) {
  
  
  return "Click to rename history";
  }

function program4(depth0,data) {
  
  var buffer = "", stack1, options;
  buffer += "\n            <div id=\"history-name\"\n                title=\"";
  options = {hash:{},inverse:self.noop,fn:self.program(5, program5, data),data:data};
  if (stack1 = helpers.local) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\">";
  if (stack1 = helpers.name) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.name; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "</div>\n            ";
  return buffer;
  }
function program5(depth0,data) {
  
  
  return "You must be logged in to edit your history name";
  }

function program7(depth0,data) {
  
  var buffer = "", stack1, options;
  buffer += "\n            <a id=\"history-tag\" title=\"";
  options = {hash:{},inverse:self.noop,fn:self.program(8, program8, data),data:data};
  if (stack1 = helpers.local) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\"\n                class=\"icon-button tags\" target=\"galaxy_main\" href=\"javascript:void(0)\"></a>\n            <a id=\"history-annotate\" title=\"";
  options = {hash:{},inverse:self.noop,fn:self.program(10, program10, data),data:data};
  if (stack1 = helpers.local) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\"\n                class=\"icon-button annotate\" target=\"galaxy_main\" href=\"javascript:void(0)\"></a>\n            ";
  return buffer;
  }
function program8(depth0,data) {
  
  
  return "Edit history tags";
  }

function program10(depth0,data) {
  
  
  return "Edit history annotation";
  }

function program12(depth0,data) {
  
  var buffer = "", stack1, options;
  buffer += "\n    <div id=\"history-tag-annotation\">\n\n        <div id=\"history-tag-area\" style=\"display: none\">\n            <strong>";
  options = {hash:{},inverse:self.noop,fn:self.program(13, program13, data),data:data};
  if (stack1 = helpers.local) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += ":</strong>\n            <div class=\"tag-elt\"></div>\n        </div>\n\n        <div id=\"history-annotation-area\" style=\"display: none\">\n            <strong>";
  options = {hash:{},inverse:self.noop,fn:self.program(15, program15, data),data:data};
  if (stack1 = helpers.local) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += ":</strong>\n            <div id=\"history-annotation-container\">\n            <div id=\"history-annotation\" class=\"editable-text\"\n                title=\"";
  options = {hash:{},inverse:self.noop,fn:self.program(17, program17, data),data:data};
  if (stack1 = helpers.local) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\">\n                ";
  stack1 = helpers['if'].call(depth0, depth0.annotation, {hash:{},inverse:self.program(21, program21, data),fn:self.program(19, program19, data),data:data});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n            </div>\n            </div>\n        </div>\n    </div>\n    ";
  return buffer;
  }
function program13(depth0,data) {
  
  
  return "Tags";
  }

function program15(depth0,data) {
  
  
  return "Annotation";
  }

function program17(depth0,data) {
  
  
  return "Click to edit annotation";
  }

function program19(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n                    ";
  if (stack1 = helpers.annotation) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.annotation; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "\n                ";
  return buffer;
  }

function program21(depth0,data) {
  
  var buffer = "", stack1, options;
  buffer += "\n                    <em>";
  options = {hash:{},inverse:self.noop,fn:self.program(22, program22, data),data:data};
  if (stack1 = helpers.local) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "</em>\n                ";
  return buffer;
  }
function program22(depth0,data) {
  
  
  return "Describe or add notes to history";
  }

function program24(depth0,data) {
  
  var buffer = "", stack1, options;
  buffer += "\n    ";
  options = {hash:{},inverse:self.noop,fn:self.program(25, program25, data),data:data};
  if (stack1 = helpers.warningmessagesmall) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.warningmessagesmall; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.warningmessagesmall) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n    ";
  return buffer;
  }
function program25(depth0,data) {
  
  var stack1, options;
  options = {hash:{},inverse:self.noop,fn:self.program(26, program26, data),data:data};
  if (stack1 = helpers.local) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { return stack1; }
  else { return ''; }
  }
function program26(depth0,data) {
  
  
  return "You are currently viewing a deleted history!";
  }

function program28(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n        <div class=\"";
  if (stack1 = helpers.status) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.status; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "message\">";
  if (stack1 = helpers.message) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.message; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "</div>\n        ";
  return buffer;
  }

function program30(depth0,data) {
  
  
  return "You are over your disk quota";
  }

function program32(depth0,data) {
  
  
  return "Tool execution is on hold until your disk usage drops below your allocated quota";
  }

function program34(depth0,data) {
  
  
  return "Your history is empty. Click 'Get Data' on the left pane to start";
  }

  buffer += "<div id=\"history-controls\">\n\n    <div id=\"history-title-area\" class=\"historyLinks\">\n        "
    + "\n        <div id=\"history-name-container\">\n            "
    + "\n            ";
  stack2 = helpers['if'].call(depth0, ((stack1 = depth0.user),stack1 == null || stack1 === false ? stack1 : stack1.email), {hash:{},inverse:self.program(4, program4, data),fn:self.program(1, program1, data),data:data});
  if(stack2 || stack2 === 0) { buffer += stack2; }
  buffer += "\n        </div>\n    </div>\n\n    <div id=\"history-subtitle-area\">\n        <div id=\"history-size\" style=\"float:left;\">";
  if (stack2 = helpers.nice_size) { stack2 = stack2.call(depth0, {hash:{},data:data}); }
  else { stack2 = depth0.nice_size; stack2 = typeof stack2 === functionType ? stack2.apply(depth0) : stack2; }
  buffer += escapeExpression(stack2)
    + "</div>\n\n        <div id=\"history-secondary-links\" style=\"float: right;\">\n            ";
  stack2 = helpers['if'].call(depth0, ((stack1 = depth0.user),stack1 == null || stack1 === false ? stack1 : stack1.email), {hash:{},inverse:self.noop,fn:self.program(7, program7, data),data:data});
  if(stack2 || stack2 === 0) { buffer += stack2; }
  buffer += "\n        </div>\n        <div style=\"clear: both;\"></div>\n    </div>\n\n    "
    + "\n    "
    + "\n    ";
  stack2 = helpers['if'].call(depth0, ((stack1 = depth0.user),stack1 == null || stack1 === false ? stack1 : stack1.email), {hash:{},inverse:self.noop,fn:self.program(12, program12, data),data:data});
  if(stack2 || stack2 === 0) { buffer += stack2; }
  buffer += "\n\n    ";
  stack2 = helpers['if'].call(depth0, depth0.deleted, {hash:{},inverse:self.noop,fn:self.program(24, program24, data),data:data});
  if(stack2 || stack2 === 0) { buffer += stack2; }
  buffer += "\n\n    <div id=\"message-container\">\n        ";
  stack2 = helpers['if'].call(depth0, depth0.message, {hash:{},inverse:self.noop,fn:self.program(28, program28, data),data:data});
  if(stack2 || stack2 === 0) { buffer += stack2; }
  buffer += "\n    </div>\n\n    <div id=\"quota-message-container\" style=\"display: none\">\n        <div id=\"quota-message\" class=\"errormessage\">\n            ";
  options = {hash:{},inverse:self.noop,fn:self.program(30, program30, data),data:data};
  if (stack2 = helpers.local) { stack2 = stack2.call(depth0, options); }
  else { stack2 = depth0.local; stack2 = typeof stack2 === functionType ? stack2.apply(depth0) : stack2; }
  if (!helpers.local) { stack2 = blockHelperMissing.call(depth0, stack2, options); }
  if(stack2 || stack2 === 0) { buffer += stack2; }
  buffer += ".\n            ";
  options = {hash:{},inverse:self.noop,fn:self.program(32, program32, data),data:data};
  if (stack2 = helpers.local) { stack2 = stack2.call(depth0, options); }
  else { stack2 = depth0.local; stack2 = typeof stack2 === functionType ? stack2.apply(depth0) : stack2; }
  if (!helpers.local) { stack2 = blockHelperMissing.call(depth0, stack2, options); }
  if(stack2 || stack2 === 0) { buffer += stack2; }
  buffer += ".\n        </div>\n    </div>\n</div>\n\n<div id=\"";
  if (stack2 = helpers.id) { stack2 = stack2.call(depth0, {hash:{},data:data}); }
  else { stack2 = depth0.id; stack2 = typeof stack2 === functionType ? stack2.apply(depth0) : stack2; }
  buffer += escapeExpression(stack2)
    + "-datasets\" class=\"history-datasets-list\"></div>\n\n<div class=\"infomessagesmall\" id=\"emptyHistoryMessage\" style=\"display: none;\">\n    ";
  options = {hash:{},inverse:self.noop,fn:self.program(34, program34, data),data:data};
  if (stack2 = helpers.local) { stack2 = stack2.call(depth0, options); }
  else { stack2 = depth0.local; stack2 = typeof stack2 === functionType ? stack2.apply(depth0) : stack2; }
  if (!helpers.local) { stack2 = blockHelperMissing.call(depth0, stack2, options); }
  if(stack2 || stack2 === 0) { buffer += stack2; }
  buffer += "\n</div>";
  return buffer;
  });
})();(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-iconButton'] = template(function (Handlebars,depth0,helpers,partials,data) {
  this.compilerInfo = [4,'>= 1.0.0'];
helpers = this.merge(helpers, Handlebars.helpers); partials = this.merge(partials, Handlebars.partials); data = data || {};
  var buffer = "", stack1, self=this;


  buffer += "\n";
  stack1 = self.invokePartial(partials.iconButton, 'iconButton', depth0, helpers, partials, data);
  if(stack1 || stack1 === 0) { buffer += stack1; }
  return buffer;
  });
})();(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-warningmessagesmall'] = template(function (Handlebars,depth0,helpers,partials,data) {
  this.compilerInfo = [4,'>= 1.0.0'];
helpers = this.merge(helpers, Handlebars.helpers); data = data || {};
  var buffer = "", stack1, functionType="function";


  buffer += " \n    <div class=\"warningmessagesmall\"><strong>";
  if (stack1 = helpers.warning) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.warning; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "</strong></div>";
  return buffer;
  });
})();