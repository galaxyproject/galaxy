(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-hda-downloadLinks'] = template(function (Handlebars,depth0,helpers,partials,data) {
  helpers = helpers || Handlebars.helpers;
  var stack1, stack2, foundHelper, tmp1, self=this, functionType="function", helperMissing=helpers.helperMissing, undef=void 0, escapeExpression=this.escapeExpression, blockHelperMissing=helpers.blockHelperMissing;

function program1(depth0,data) {
  
  var buffer = "", stack1, stack2;
  buffer += "\n<div popupmenu=\"dataset-";
  foundHelper = helpers.id;
  stack1 = foundHelper || depth0.id;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "id", { hash: {} }); }
  buffer += escapeExpression(stack1) + "-popup\">\n    <a class=\"action-button\" href=\"";
  foundHelper = helpers.urls;
  stack1 = foundHelper || depth0.urls;
  stack1 = (stack1 === null || stack1 === undefined || stack1 === false ? stack1 : stack1.download);
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "urls.download", { hash: {} }); }
  buffer += escapeExpression(stack1) + "\">";
  foundHelper = helpers.local;
  stack1 = foundHelper || depth0.local;
  tmp1 = self.program(2, program2, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  if(foundHelper && typeof stack1 === functionType) { stack1 = stack1.call(depth0, tmp1); }
  else { stack1 = blockHelperMissing.call(depth0, stack1, tmp1); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "</a>\n    <a>";
  foundHelper = helpers.local;
  stack1 = foundHelper || depth0.local;
  tmp1 = self.program(4, program4, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  if(foundHelper && typeof stack1 === functionType) { stack1 = stack1.call(depth0, tmp1); }
  else { stack1 = blockHelperMissing.call(depth0, stack1, tmp1); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "</a>\n    ";
  foundHelper = helpers.urls;
  stack1 = foundHelper || depth0.urls;
  stack1 = (stack1 === null || stack1 === undefined || stack1 === false ? stack1 : stack1.meta_download);
  stack2 = helpers.each;
  tmp1 = self.program(6, program6, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  stack1 = stack2.call(depth0, stack1, tmp1);
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n</div>\n<div style=\"float:left;\" class=\"menubutton split popup\" id=\"dataset-";
  foundHelper = helpers.id;
  stack1 = foundHelper || depth0.id;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "id", { hash: {} }); }
  buffer += escapeExpression(stack1) + "-popup\">\n    <a href=\"";
  foundHelper = helpers.urls;
  stack1 = foundHelper || depth0.urls;
  stack1 = (stack1 === null || stack1 === undefined || stack1 === false ? stack1 : stack1.download);
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "urls.download", { hash: {} }); }
  buffer += escapeExpression(stack1) + "\" title=\"";
  foundHelper = helpers.local;
  stack1 = foundHelper || depth0.local;
  tmp1 = self.program(9, program9, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  if(foundHelper && typeof stack1 === functionType) { stack1 = stack1.call(depth0, tmp1); }
  else { stack1 = blockHelperMissing.call(depth0, stack1, tmp1); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\" class=\"icon-button disk tooltip\"></a>\n</div>\n";
  return buffer;}
function program2(depth0,data) {
  
  
  return "Download Dataset";}

function program4(depth0,data) {
  
  
  return "Additional Files";}

function program6(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n    <a class=\"action-button\" href=\"";
  foundHelper = helpers.url;
  stack1 = foundHelper || depth0.url;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "url", { hash: {} }); }
  buffer += escapeExpression(stack1) + "\">";
  foundHelper = helpers.local;
  stack1 = foundHelper || depth0.local;
  tmp1 = self.program(7, program7, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  if(foundHelper && typeof stack1 === functionType) { stack1 = stack1.call(depth0, tmp1); }
  else { stack1 = blockHelperMissing.call(depth0, stack1, tmp1); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += " ";
  foundHelper = helpers.file_type;
  stack1 = foundHelper || depth0.file_type;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "file_type", { hash: {} }); }
  buffer += escapeExpression(stack1) + "</a>\n    ";
  return buffer;}
function program7(depth0,data) {
  
  
  return "Download";}

function program9(depth0,data) {
  
  
  return "Download";}

function program11(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n";
  buffer += "\n<a href=\"";
  foundHelper = helpers.urls;
  stack1 = foundHelper || depth0.urls;
  stack1 = (stack1 === null || stack1 === undefined || stack1 === false ? stack1 : stack1.download);
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "urls.download", { hash: {} }); }
  buffer += escapeExpression(stack1) + "\" title=\"";
  foundHelper = helpers.local;
  stack1 = foundHelper || depth0.local;
  tmp1 = self.program(12, program12, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  if(foundHelper && typeof stack1 === functionType) { stack1 = stack1.call(depth0, tmp1); }
  else { stack1 = blockHelperMissing.call(depth0, stack1, tmp1); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\" class=\"icon-button disk tooltip\"></a>\n";
  return buffer;}
function program12(depth0,data) {
  
  
  return "Download";}

  foundHelper = helpers.urls;
  stack1 = foundHelper || depth0.urls;
  stack1 = (stack1 === null || stack1 === undefined || stack1 === false ? stack1 : stack1.meta_download);
  stack2 = helpers['if'];
  tmp1 = self.program(1, program1, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.program(11, program11, data);
  stack1 = stack2.call(depth0, stack1, tmp1);
  if(stack1 || stack1 === 0) { return stack1; }
  else { return ''; }});
})();