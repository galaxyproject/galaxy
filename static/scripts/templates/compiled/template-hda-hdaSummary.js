(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-hda-hdaSummary'] = template(function (Handlebars,depth0,helpers,partials,data) {
  helpers = helpers || Handlebars.helpers;
  var buffer = "", stack1, stack2, foundHelper, tmp1, self=this, functionType="function", helperMissing=helpers.helperMissing, undef=void 0, escapeExpression=this.escapeExpression, blockHelperMissing=helpers.blockHelperMissing;

function program1(depth0,data) {
  
  
  return "format: ";}

function program3(depth0,data) {
  
  
  return "database: ";}

function program5(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n        <a class=\"metadata-dbkey\" href=\"";
  foundHelper = helpers.urls;
  stack1 = foundHelper || depth0.urls;
  stack1 = (stack1 === null || stack1 === undefined || stack1 === false ? stack1 : stack1.edit);
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "urls.edit", { hash: {} }); }
  buffer += escapeExpression(stack1) + "\" target=\"galaxy_main\">";
  foundHelper = helpers.metadata_dbkey;
  stack1 = foundHelper || depth0.metadata_dbkey;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "metadata_dbkey", { hash: {} }); }
  buffer += escapeExpression(stack1) + "</a>\n    ";
  return buffer;}

function program7(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n        <span class=\"metadata-dbkey ";
  foundHelper = helpers.metadata_dbkey;
  stack1 = foundHelper || depth0.metadata_dbkey;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "metadata_dbkey", { hash: {} }); }
  buffer += escapeExpression(stack1) + "\">";
  foundHelper = helpers.metadata_dbkey;
  stack1 = foundHelper || depth0.metadata_dbkey;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "metadata_dbkey", { hash: {} }); }
  buffer += escapeExpression(stack1) + "</span>\n    ";
  return buffer;}

function program9(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n<div class=\"hda-info\"> ";
  foundHelper = helpers.misc_info;
  stack1 = foundHelper || depth0.misc_info;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "misc_info", { hash: {} }); }
  buffer += escapeExpression(stack1) + " </div>\n";
  return buffer;}

  buffer += "<div class=\"hda-summary\">\n    ";
  foundHelper = helpers.misc_blurb;
  stack1 = foundHelper || depth0.misc_blurb;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "misc_blurb", { hash: {} }); }
  buffer += escapeExpression(stack1) + "<br />\n    ";
  foundHelper = helpers.local;
  stack1 = foundHelper || depth0.local;
  tmp1 = self.program(1, program1, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  if(foundHelper && typeof stack1 === functionType) { stack1 = stack1.call(depth0, tmp1); }
  else { stack1 = blockHelperMissing.call(depth0, stack1, tmp1); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "<span class=\"";
  foundHelper = helpers.data_type;
  stack1 = foundHelper || depth0.data_type;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "data_type", { hash: {} }); }
  buffer += escapeExpression(stack1) + "\">";
  foundHelper = helpers.data_type;
  stack1 = foundHelper || depth0.data_type;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "data_type", { hash: {} }); }
  buffer += escapeExpression(stack1) + "</span>,\n    ";
  foundHelper = helpers.local;
  stack1 = foundHelper || depth0.local;
  tmp1 = self.program(3, program3, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  if(foundHelper && typeof stack1 === functionType) { stack1 = stack1.call(depth0, tmp1); }
  else { stack1 = blockHelperMissing.call(depth0, stack1, tmp1); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n    ";
  foundHelper = helpers.dbkey_unknown_and_editable;
  stack1 = foundHelper || depth0.dbkey_unknown_and_editable;
  stack2 = helpers['if'];
  tmp1 = self.program(5, program5, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.program(7, program7, data);
  stack1 = stack2.call(depth0, stack1, tmp1);
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n</div>\n";
  foundHelper = helpers.misc_info;
  stack1 = foundHelper || depth0.misc_info;
  stack2 = helpers['if'];
  tmp1 = self.program(9, program9, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  stack1 = stack2.call(depth0, stack1, tmp1);
  if(stack1 || stack1 === 0) { buffer += stack1; }
  return buffer;});
})();