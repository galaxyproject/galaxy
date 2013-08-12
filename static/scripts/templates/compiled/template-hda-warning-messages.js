(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-hda-warning-messages'] = template(function (Handlebars,depth0,helpers,partials,data) {
  helpers = helpers || Handlebars.helpers;
  var buffer = "", stack1, stack2, foundHelper, tmp1, self=this, functionType="function", helperMissing=helpers.helperMissing, undef=void 0, escapeExpression=this.escapeExpression, blockHelperMissing=helpers.blockHelperMissing;

function program1(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n<div class=\"errormessagesmall\">\n    ";
  foundHelper = helpers.local;
  stack1 = foundHelper || depth0.local;
  tmp1 = self.program(2, program2, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  if(foundHelper && typeof stack1 === functionType) { stack1 = stack1.call(depth0, tmp1); }
  else { stack1 = blockHelperMissing.call(depth0, stack1, tmp1); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += ":\n    ";
  foundHelper = helpers.local;
  stack1 = foundHelper || depth0.local;
  tmp1 = self.program(4, program4, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  if(foundHelper && typeof stack1 === functionType) { stack1 = stack1.call(depth0, tmp1); }
  else { stack1 = blockHelperMissing.call(depth0, stack1, tmp1); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n</div>\n";
  return buffer;}
function program2(depth0,data) {
  
  
  return "There was an error getting the data for this dataset";}

function program4(depth0,data) {
  
  var stack1;
  foundHelper = helpers.error;
  stack1 = foundHelper || depth0.error;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "error", { hash: {} }); }
  return escapeExpression(stack1);}

function program6(depth0,data) {
  
  var stack1, stack2;
  foundHelper = helpers.purged;
  stack1 = foundHelper || depth0.purged;
  stack2 = helpers.unless;
  tmp1 = self.program(7, program7, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  stack1 = stack2.call(depth0, stack1, tmp1);
  if(stack1 || stack1 === 0) { return stack1; }
  else { return ''; }}
function program7(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n";
  foundHelper = helpers.warningmessagesmall;
  stack1 = foundHelper || depth0.warningmessagesmall;
  tmp1 = self.program(8, program8, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  if(foundHelper && typeof stack1 === functionType) { stack1 = stack1.call(depth0, tmp1); }
  else { stack1 = blockHelperMissing.call(depth0, stack1, tmp1); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n";
  return buffer;}
function program8(depth0,data) {
  
  var buffer = "", stack1, stack2;
  buffer += "\n    ";
  foundHelper = helpers.local;
  stack1 = foundHelper || depth0.local;
  tmp1 = self.program(9, program9, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  if(foundHelper && typeof stack1 === functionType) { stack1 = stack1.call(depth0, tmp1); }
  else { stack1 = blockHelperMissing.call(depth0, stack1, tmp1); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n    ";
  foundHelper = helpers.urls;
  stack1 = foundHelper || depth0.urls;
  stack1 = (stack1 === null || stack1 === undefined || stack1 === false ? stack1 : stack1.undelete);
  stack2 = helpers['if'];
  tmp1 = self.program(11, program11, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  stack1 = stack2.call(depth0, stack1, tmp1);
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n";
  return buffer;}
function program9(depth0,data) {
  
  
  return "This dataset has been deleted.";}

function program11(depth0,data) {
  
  var buffer = "", stack1, stack2;
  buffer += "\n        ";
  buffer += "\n        Click <a href=\"";
  foundHelper = helpers.urls;
  stack1 = foundHelper || depth0.urls;
  stack1 = (stack1 === null || stack1 === undefined || stack1 === false ? stack1 : stack1.undelete);
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "urls.undelete", { hash: {} }); }
  buffer += escapeExpression(stack1) + "\" class=\"historyItemUndelete\" id=\"historyItemUndeleter-";
  foundHelper = helpers.id;
  stack1 = foundHelper || depth0.id;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "id", { hash: {} }); }
  buffer += escapeExpression(stack1) + "\"\n                 target=\"galaxy_history\">here</a> to undelete it\n        ";
  foundHelper = helpers.urls;
  stack1 = foundHelper || depth0.urls;
  stack1 = (stack1 === null || stack1 === undefined || stack1 === false ? stack1 : stack1.purge);
  stack2 = helpers['if'];
  tmp1 = self.program(12, program12, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  stack1 = stack2.call(depth0, stack1, tmp1);
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n    ";
  return buffer;}
function program12(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n        or <a href=\"";
  foundHelper = helpers.urls;
  stack1 = foundHelper || depth0.urls;
  stack1 = (stack1 === null || stack1 === undefined || stack1 === false ? stack1 : stack1.purge);
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "urls.purge", { hash: {} }); }
  buffer += escapeExpression(stack1) + "\" class=\"historyItemPurge\" id=\"historyItemPurger-";
  foundHelper = helpers.id;
  stack1 = foundHelper || depth0.id;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "id", { hash: {} }); }
  buffer += escapeExpression(stack1) + "\"\n           target=\"galaxy_history\">here</a> to immediately remove it from disk\n        ";
  return buffer;}

function program14(depth0,data) {
  
  var stack1;
  foundHelper = helpers.warningmessagesmall;
  stack1 = foundHelper || depth0.warningmessagesmall;
  tmp1 = self.program(15, program15, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  if(foundHelper && typeof stack1 === functionType) { stack1 = stack1.call(depth0, tmp1); }
  else { stack1 = blockHelperMissing.call(depth0, stack1, tmp1); }
  if(stack1 || stack1 === 0) { return stack1; }
  else { return ''; }}
function program15(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n    ";
  foundHelper = helpers.local;
  stack1 = foundHelper || depth0.local;
  tmp1 = self.program(16, program16, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  if(foundHelper && typeof stack1 === functionType) { stack1 = stack1.call(depth0, tmp1); }
  else { stack1 = blockHelperMissing.call(depth0, stack1, tmp1); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n";
  return buffer;}
function program16(depth0,data) {
  
  
  return "This dataset has been deleted and removed from disk.";}

function program18(depth0,data) {
  
  var stack1;
  foundHelper = helpers.warningmessagesmall;
  stack1 = foundHelper || depth0.warningmessagesmall;
  tmp1 = self.program(19, program19, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  if(foundHelper && typeof stack1 === functionType) { stack1 = stack1.call(depth0, tmp1); }
  else { stack1 = blockHelperMissing.call(depth0, stack1, tmp1); }
  if(stack1 || stack1 === 0) { return stack1; }
  else { return ''; }}
function program19(depth0,data) {
  
  var buffer = "", stack1, stack2;
  buffer += "\n    ";
  foundHelper = helpers.local;
  stack1 = foundHelper || depth0.local;
  tmp1 = self.program(20, program20, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  if(foundHelper && typeof stack1 === functionType) { stack1 = stack1.call(depth0, tmp1); }
  else { stack1 = blockHelperMissing.call(depth0, stack1, tmp1); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n    ";
  foundHelper = helpers.urls;
  stack1 = foundHelper || depth0.urls;
  stack1 = (stack1 === null || stack1 === undefined || stack1 === false ? stack1 : stack1.unhide);
  stack2 = helpers['if'];
  tmp1 = self.program(22, program22, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  stack1 = stack2.call(depth0, stack1, tmp1);
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n";
  return buffer;}
function program20(depth0,data) {
  
  
  return "This dataset has been hidden.";}

function program22(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n        Click <a href=\"";
  foundHelper = helpers.urls;
  stack1 = foundHelper || depth0.urls;
  stack1 = (stack1 === null || stack1 === undefined || stack1 === false ? stack1 : stack1.unhide);
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "urls.unhide", { hash: {} }); }
  buffer += escapeExpression(stack1) + "\" class=\"historyItemUnhide\" id=\"historyItemUnhider-";
  foundHelper = helpers.id;
  stack1 = foundHelper || depth0.id;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "id", { hash: {} }); }
  buffer += escapeExpression(stack1) + "\"\n                 target=\"galaxy_history\">here</a> to unhide it\n    ";
  return buffer;}

  foundHelper = helpers.error;
  stack1 = foundHelper || depth0.error;
  stack2 = helpers['if'];
  tmp1 = self.program(1, program1, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  stack1 = stack2.call(depth0, stack1, tmp1);
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n\n";
  foundHelper = helpers.deleted;
  stack1 = foundHelper || depth0.deleted;
  stack2 = helpers['if'];
  tmp1 = self.program(6, program6, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  stack1 = stack2.call(depth0, stack1, tmp1);
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n\n";
  foundHelper = helpers.purged;
  stack1 = foundHelper || depth0.purged;
  stack2 = helpers['if'];
  tmp1 = self.program(14, program14, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  stack1 = stack2.call(depth0, stack1, tmp1);
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n\n";
  foundHelper = helpers.visible;
  stack1 = foundHelper || depth0.visible;
  stack2 = helpers.unless;
  tmp1 = self.program(18, program18, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  stack1 = stack2.call(depth0, stack1, tmp1);
  if(stack1 || stack1 === 0) { buffer += stack1; }
  return buffer;});
})();