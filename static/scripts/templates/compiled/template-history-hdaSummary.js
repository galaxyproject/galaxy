(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-history-hdaSummary'] = template(function (Handlebars,depth0,helpers,partials,data) {
  helpers = helpers || Handlebars.helpers;
  var buffer = "", stack1, foundHelper, functionType="function", escapeExpression=this.escapeExpression, self=this;

function program1(depth0,data) {
  
  var buffer = "", stack1, foundHelper;
  buffer += "\n        <a href=\"";
  stack1 = depth0.urls;
  stack1 = stack1 == null || stack1 === false ? stack1 : stack1.edit;
  stack1 = typeof stack1 === functionType ? stack1() : stack1;
  buffer += escapeExpression(stack1) + "\" target=\"galaxy_main\">";
  foundHelper = helpers.metadata_dbkey;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.metadata_dbkey; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "</a>\n    ";
  return buffer;}

function program3(depth0,data) {
  
  var buffer = "", stack1, foundHelper;
  buffer += "\n        <span class=\"";
  foundHelper = helpers.metadata_dbkey;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.metadata_dbkey; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "\">";
  foundHelper = helpers.metadata_dbkey;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.metadata_dbkey; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "</span>\n    ";
  return buffer;}

function program5(depth0,data) {
  
  var buffer = "", stack1, foundHelper;
  buffer += "\n<div class=\"hda-info\">";
  foundHelper = helpers.misc_info;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.misc_info; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "</div>\n";
  return buffer;}

  buffer += "<div class=\"hda-summary\">\n    ";
  foundHelper = helpers.misc_blurb;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.misc_blurb; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "<br />\n    format: <span class=\"";
  foundHelper = helpers.data_type;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.data_type; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "\">";
  foundHelper = helpers.data_type;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.data_type; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "</span>,\n    database:\n    ";
  stack1 = depth0.dbkey_unknown_and_editable;
  stack1 = helpers['if'].call(depth0, stack1, {hash:{},inverse:self.program(3, program3, data),fn:self.program(1, program1, data)});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n</div>\n";
  stack1 = depth0.misc_info;
  stack1 = helpers['if'].call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(5, program5, data)});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  return buffer;});
})();