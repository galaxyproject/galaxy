(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-history-historyPanel'] = template(function (Handlebars,depth0,helpers,partials,data) {
  helpers = helpers || Handlebars.helpers;
  var buffer = "", stack1, stack2, foundHelper, tmp1, self=this, functionType="function", blockHelperMissing=helpers.blockHelperMissing, helperMissing=helpers.helperMissing, undef=void 0, escapeExpression=this.escapeExpression;

function program1(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n            <div id=\"history-name\" class=\"tooltip editable-text\"\n                title=\"";
  foundHelper = helpers.local;
  stack1 = foundHelper || depth0.local;
  tmp1 = self.program(2, program2, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  if(foundHelper && typeof stack1 === functionType) { stack1 = stack1.call(depth0, tmp1); }
  else { stack1 = blockHelperMissing.call(depth0, stack1, tmp1); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\">";
  foundHelper = helpers.name;
  stack1 = foundHelper || depth0.name;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "name", { hash: {} }); }
  buffer += escapeExpression(stack1) + "</div>\n            ";
  return buffer;}
function program2(depth0,data) {
  
  
  return "Click to rename history";}

function program4(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n            <div id=\"history-name\" class=\"tooltip\"\n                title=\"";
  foundHelper = helpers.local;
  stack1 = foundHelper || depth0.local;
  tmp1 = self.program(5, program5, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  if(foundHelper && typeof stack1 === functionType) { stack1 = stack1.call(depth0, tmp1); }
  else { stack1 = blockHelperMissing.call(depth0, stack1, tmp1); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\">";
  foundHelper = helpers.name;
  stack1 = foundHelper || depth0.name;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "name", { hash: {} }); }
  buffer += escapeExpression(stack1) + "</div>\n            ";
  return buffer;}
function program5(depth0,data) {
  
  
  return "You must be logged in to edit your history name";}

function program7(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n            <a id=\"history-tag\" title=\"";
  foundHelper = helpers.local;
  stack1 = foundHelper || depth0.local;
  tmp1 = self.program(8, program8, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  if(foundHelper && typeof stack1 === functionType) { stack1 = stack1.call(depth0, tmp1); }
  else { stack1 = blockHelperMissing.call(depth0, stack1, tmp1); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\"\n                class=\"icon-button tags tooltip\" target=\"galaxy_main\" href=\"javascript:void(0)\"></a>\n            <a id=\"history-annotate\" title=\"";
  foundHelper = helpers.local;
  stack1 = foundHelper || depth0.local;
  tmp1 = self.program(10, program10, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  if(foundHelper && typeof stack1 === functionType) { stack1 = stack1.call(depth0, tmp1); }
  else { stack1 = blockHelperMissing.call(depth0, stack1, tmp1); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\"\n                class=\"icon-button annotate tooltip\" target=\"galaxy_main\" href=\"javascript:void(0)\"></a>\n            ";
  return buffer;}
function program8(depth0,data) {
  
  
  return "Edit history tags";}

function program10(depth0,data) {
  
  
  return "Edit history annotation";}

function program12(depth0,data) {
  
  var buffer = "", stack1, stack2;
  buffer += "\n    <div id=\"history-tag-annotation\">\n\n        <div id=\"history-tag-area\" style=\"display: none\">\n            <strong>";
  foundHelper = helpers.local;
  stack1 = foundHelper || depth0.local;
  tmp1 = self.program(13, program13, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  if(foundHelper && typeof stack1 === functionType) { stack1 = stack1.call(depth0, tmp1); }
  else { stack1 = blockHelperMissing.call(depth0, stack1, tmp1); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += ":</strong>\n            <div class=\"tag-elt\"></div>\n        </div>\n\n        <div id=\"history-annotation-area\" style=\"display: none\">\n            <strong>";
  foundHelper = helpers.local;
  stack1 = foundHelper || depth0.local;
  tmp1 = self.program(15, program15, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  if(foundHelper && typeof stack1 === functionType) { stack1 = stack1.call(depth0, tmp1); }
  else { stack1 = blockHelperMissing.call(depth0, stack1, tmp1); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += ":</strong>\n            <div id=\"history-annotation-container\">\n            <div id=\"history-annotation\" class=\"tooltip editable-text\"\n                title=\"";
  foundHelper = helpers.local;
  stack1 = foundHelper || depth0.local;
  tmp1 = self.program(17, program17, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  if(foundHelper && typeof stack1 === functionType) { stack1 = stack1.call(depth0, tmp1); }
  else { stack1 = blockHelperMissing.call(depth0, stack1, tmp1); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\">\n                ";
  foundHelper = helpers.annotation;
  stack1 = foundHelper || depth0.annotation;
  stack2 = helpers['if'];
  tmp1 = self.program(19, program19, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.program(21, program21, data);
  stack1 = stack2.call(depth0, stack1, tmp1);
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n            </div>\n            </div>\n        </div>\n    </div>\n    ";
  return buffer;}
function program13(depth0,data) {
  
  
  return "Tags";}

function program15(depth0,data) {
  
  
  return "Annotation";}

function program17(depth0,data) {
  
  
  return "Click to edit annotation";}

function program19(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n                    ";
  foundHelper = helpers.annotation;
  stack1 = foundHelper || depth0.annotation;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "annotation", { hash: {} }); }
  buffer += escapeExpression(stack1) + "\n                ";
  return buffer;}

function program21(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n                    <em>";
  foundHelper = helpers.local;
  stack1 = foundHelper || depth0.local;
  tmp1 = self.program(22, program22, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  if(foundHelper && typeof stack1 === functionType) { stack1 = stack1.call(depth0, tmp1); }
  else { stack1 = blockHelperMissing.call(depth0, stack1, tmp1); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "</em>\n                ";
  return buffer;}
function program22(depth0,data) {
  
  
  return "Describe or add notes to history";}

function program24(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n    ";
  foundHelper = helpers.warningmessagesmall;
  stack1 = foundHelper || depth0.warningmessagesmall;
  tmp1 = self.program(25, program25, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  if(foundHelper && typeof stack1 === functionType) { stack1 = stack1.call(depth0, tmp1); }
  else { stack1 = blockHelperMissing.call(depth0, stack1, tmp1); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n    ";
  return buffer;}
function program25(depth0,data) {
  
  var stack1;
  foundHelper = helpers.local;
  stack1 = foundHelper || depth0.local;
  tmp1 = self.program(26, program26, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  if(foundHelper && typeof stack1 === functionType) { stack1 = stack1.call(depth0, tmp1); }
  else { stack1 = blockHelperMissing.call(depth0, stack1, tmp1); }
  if(stack1 || stack1 === 0) { return stack1; }
  else { return ''; }}
function program26(depth0,data) {
  
  
  return "You are currently viewing a deleted history!";}

function program28(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n        <div class=\"";
  foundHelper = helpers.status;
  stack1 = foundHelper || depth0.status;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "status", { hash: {} }); }
  buffer += escapeExpression(stack1) + "message\">";
  foundHelper = helpers.message;
  stack1 = foundHelper || depth0.message;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "message", { hash: {} }); }
  buffer += escapeExpression(stack1) + "</div>\n        ";
  return buffer;}

function program30(depth0,data) {
  
  
  return "You are over your disk quota";}

function program32(depth0,data) {
  
  
  return "Tool execution is on hold until your disk usage drops below your allocated quota";}

function program34(depth0,data) {
  
  
  return "Your history is empty. Click 'Get Data' on the left pane to start";}

  buffer += "<div id=\"history-controls\">\n\n    <div id=\"history-title-area\" class=\"historyLinks\">\n        ";
  buffer += "\n        <div id=\"history-name-container\">\n            ";
  buffer += "\n            ";
  foundHelper = helpers.user;
  stack1 = foundHelper || depth0.user;
  stack1 = (stack1 === null || stack1 === undefined || stack1 === false ? stack1 : stack1.email);
  stack2 = helpers['if'];
  tmp1 = self.program(1, program1, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.program(4, program4, data);
  stack1 = stack2.call(depth0, stack1, tmp1);
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n        </div>\n    </div>\n\n    <div id=\"history-subtitle-area\">\n        <div id=\"history-size\" style=\"float:left;\">";
  foundHelper = helpers.nice_size;
  stack1 = foundHelper || depth0.nice_size;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "nice_size", { hash: {} }); }
  buffer += escapeExpression(stack1) + "</div>\n\n        <div id=\"history-secondary-links\" style=\"float: right;\">\n            ";
  foundHelper = helpers.user;
  stack1 = foundHelper || depth0.user;
  stack1 = (stack1 === null || stack1 === undefined || stack1 === false ? stack1 : stack1.email);
  stack2 = helpers['if'];
  tmp1 = self.program(7, program7, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  stack1 = stack2.call(depth0, stack1, tmp1);
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n        </div>\n        <div style=\"clear: both;\"></div>\n    </div>\n\n    ";
  buffer += "\n    ";
  buffer += "\n    ";
  foundHelper = helpers.user;
  stack1 = foundHelper || depth0.user;
  stack1 = (stack1 === null || stack1 === undefined || stack1 === false ? stack1 : stack1.email);
  stack2 = helpers['if'];
  tmp1 = self.program(12, program12, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  stack1 = stack2.call(depth0, stack1, tmp1);
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n\n    ";
  foundHelper = helpers.deleted;
  stack1 = foundHelper || depth0.deleted;
  stack2 = helpers['if'];
  tmp1 = self.program(24, program24, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  stack1 = stack2.call(depth0, stack1, tmp1);
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n\n    <div id=\"message-container\">\n        ";
  foundHelper = helpers.message;
  stack1 = foundHelper || depth0.message;
  stack2 = helpers['if'];
  tmp1 = self.program(28, program28, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  stack1 = stack2.call(depth0, stack1, tmp1);
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n    </div>\n\n    <div id=\"quota-message-container\" style=\"display: none\">\n        <div id=\"quota-message\" class=\"errormessage\">\n            ";
  foundHelper = helpers.local;
  stack1 = foundHelper || depth0.local;
  tmp1 = self.program(30, program30, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  if(foundHelper && typeof stack1 === functionType) { stack1 = stack1.call(depth0, tmp1); }
  else { stack1 = blockHelperMissing.call(depth0, stack1, tmp1); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += ".\n            ";
  foundHelper = helpers.local;
  stack1 = foundHelper || depth0.local;
  tmp1 = self.program(32, program32, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  if(foundHelper && typeof stack1 === functionType) { stack1 = stack1.call(depth0, tmp1); }
  else { stack1 = blockHelperMissing.call(depth0, stack1, tmp1); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += ".\n        </div>\n    </div>\n</div>\n\n<div id=\"";
  foundHelper = helpers.id;
  stack1 = foundHelper || depth0.id;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "id", { hash: {} }); }
  buffer += escapeExpression(stack1) + "-datasets\" class=\"history-datasets-list\"></div>\n\n<div class=\"infomessagesmall\" id=\"emptyHistoryMessage\" style=\"display: none;\">\n    ";
  foundHelper = helpers.local;
  stack1 = foundHelper || depth0.local;
  tmp1 = self.program(34, program34, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  if(foundHelper && typeof stack1 === functionType) { stack1 = stack1.call(depth0, tmp1); }
  else { stack1 = blockHelperMissing.call(depth0, stack1, tmp1); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n</div>";
  return buffer;});
})();