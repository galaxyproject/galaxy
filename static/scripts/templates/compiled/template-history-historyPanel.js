(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-history-historyPanel'] = template(function (Handlebars,depth0,helpers,partials,data) {
  helpers = helpers || Handlebars.helpers;
  var buffer = "", stack1, foundHelper, self=this, functionType="function", blockHelperMissing=helpers.blockHelperMissing, escapeExpression=this.escapeExpression;

function program1(depth0,data) {
  
  var buffer = "", stack1, foundHelper;
  buffer += "\n            <div id=\"history-name\" class=\"tooltip editable-text\"\n                title=\"";
  foundHelper = helpers.local;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{},inverse:self.noop,fn:self.program(2, program2, data)}); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(2, program2, data)}); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\">";
  foundHelper = helpers.name;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.name; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "</div>\n            ";
  return buffer;}
function program2(depth0,data) {
  
  
  return "Click to rename history";}

function program4(depth0,data) {
  
  var buffer = "", stack1, foundHelper;
  buffer += "\n            <div id=\"history-name\" class=\"tooltip\"\n                title=\"";
  foundHelper = helpers.local;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{},inverse:self.noop,fn:self.program(5, program5, data)}); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(5, program5, data)}); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\">";
  foundHelper = helpers.name;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.name; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "</div>\n            ";
  return buffer;}
function program5(depth0,data) {
  
  
  return "You must be logged in to edit your history name";}

function program7(depth0,data) {
  
  
  return "Click to see more actions";}

function program9(depth0,data) {
  
  var buffer = "", stack1, foundHelper;
  buffer += "\n        <div id=\"history-secondary-links\" style=\"float: right;\">\n            <a id=\"history-tag\" title=\"";
  foundHelper = helpers.local;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{},inverse:self.noop,fn:self.program(10, program10, data)}); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(10, program10, data)}); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\"\n                class=\"icon-button tags tooltip\" target=\"galaxy_main\" href=\"javascript:void(0)\"></a>\n            <a id=\"history-annotate\" title=\"";
  foundHelper = helpers.local;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{},inverse:self.noop,fn:self.program(12, program12, data)}); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(12, program12, data)}); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\"\n                class=\"icon-button annotate tooltip\" target=\"galaxy_main\" href=\"javascript:void(0)\"></a>\n        </div>\n        ";
  return buffer;}
function program10(depth0,data) {
  
  
  return "Edit history tags";}

function program12(depth0,data) {
  
  
  return "Edit history annotation";}

function program14(depth0,data) {
  
  var buffer = "", stack1, foundHelper;
  buffer += "\n    ";
  foundHelper = helpers.warningmessagesmall;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{},inverse:self.noop,fn:self.program(15, program15, data)}); }
  else { stack1 = depth0.warningmessagesmall; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  if (!helpers.warningmessagesmall) { stack1 = blockHelperMissing.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(15, program15, data)}); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n    ";
  return buffer;}
function program15(depth0,data) {
  
  var stack1, foundHelper;
  foundHelper = helpers.local;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{},inverse:self.noop,fn:self.program(16, program16, data)}); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(16, program16, data)}); }
  if(stack1 || stack1 === 0) { return stack1; }
  else { return ''; }}
function program16(depth0,data) {
  
  
  return "You are currently viewing a deleted history!";}

function program18(depth0,data) {
  
  var buffer = "", stack1, foundHelper;
  buffer += "\n    <div id=\"history-tag-annotation\">\n\n        <div id=\"history-tag-area\" style=\"display: none\">\n            <strong>";
  foundHelper = helpers.local;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{},inverse:self.noop,fn:self.program(19, program19, data)}); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(19, program19, data)}); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += ":</strong>\n            <div class=\"tag-elt\"></div>\n        </div>\n\n        <div id=\"history-annotation-area\" style=\"display: none\">\n            <strong>";
  foundHelper = helpers.local;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{},inverse:self.noop,fn:self.program(21, program21, data)}); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(21, program21, data)}); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += ":</strong>\n            <div id=\"history-annotation-container\">\n            <div id=\"history-annotation\" class=\"tooltip editable-text\"\n                title=\"";
  foundHelper = helpers.local;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{},inverse:self.noop,fn:self.program(23, program23, data)}); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(23, program23, data)}); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\">\n                ";
  stack1 = depth0.annotation;
  stack1 = helpers['if'].call(depth0, stack1, {hash:{},inverse:self.program(27, program27, data),fn:self.program(25, program25, data)});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n            </div>\n            </div>\n        </div>\n    </div>\n    ";
  return buffer;}
function program19(depth0,data) {
  
  
  return "Tags";}

function program21(depth0,data) {
  
  
  return "Annotation";}

function program23(depth0,data) {
  
  
  return "Click to edit annotation";}

function program25(depth0,data) {
  
  var buffer = "", stack1, foundHelper;
  buffer += "\n                    ";
  foundHelper = helpers.annotation;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.annotation; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "\n                ";
  return buffer;}

function program27(depth0,data) {
  
  var buffer = "", stack1, foundHelper;
  buffer += "\n                    <em>";
  foundHelper = helpers.local;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{},inverse:self.noop,fn:self.program(28, program28, data)}); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(28, program28, data)}); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "</em>\n                ";
  return buffer;}
function program28(depth0,data) {
  
  
  return "Describe or add notes to history";}

function program30(depth0,data) {
  
  var buffer = "", stack1, foundHelper;
  buffer += "\n    <div id=\"message-container\">\n        <div class=\"";
  foundHelper = helpers.status;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.status; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "message\">\n        ";
  foundHelper = helpers.message;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.message; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "\n        </div><br />\n    </div>\n    ";
  return buffer;}

function program32(depth0,data) {
  
  
  return "You are over your disk quota.\n            Tool execution is on hold until your disk usage drops below your allocated quota.";}

function program34(depth0,data) {
  
  
  return "Your history is empty. Click 'Get Data' on the left pane to start";}

  buffer += "<div id=\"history-controls\">\n    <div id=\"history-title-area\" class=\"historyLinks\">\n\n        ";
  buffer += "\n        <div id=\"history-name-container\" style=\"float: left;\">\n            ";
  buffer += "\n            ";
  stack1 = depth0.user;
  stack1 = stack1 == null || stack1 === false ? stack1 : stack1.email;
  stack1 = helpers['if'].call(depth0, stack1, {hash:{},inverse:self.program(4, program4, data),fn:self.program(1, program1, data)});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n        </div>\n\n        <a id=\"history-action-popup\" class=\"tooltip\" title=\"";
  foundHelper = helpers.local;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{},inverse:self.noop,fn:self.program(7, program7, data)}); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(7, program7, data)}); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\"\n            href=\"javascript:void(0);\" style=\"float: right;\">\n            <span class=\"ficon cogs large\"></span>\n        </a>\n        <div style=\"clear: both;\"></div>\n    </div>\n\n    <div id=\"history-subtitle-area\">\n        <div id=\"history-size\" style=\"float:left;\">";
  foundHelper = helpers.nice_size;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.nice_size; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "</div>\n        ";
  stack1 = depth0.user;
  stack1 = stack1 == null || stack1 === false ? stack1 : stack1.email;
  stack1 = helpers['if'].call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(9, program9, data)});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n        <div style=\"clear: both;\"></div>\n    </div>\n\n    ";
  stack1 = depth0.deleted;
  stack1 = helpers['if'].call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(14, program14, data)});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n\n    ";
  buffer += "\n    ";
  buffer += "\n    ";
  stack1 = depth0.user;
  stack1 = stack1 == null || stack1 === false ? stack1 : stack1.email;
  stack1 = helpers['if'].call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(18, program18, data)});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n\n    ";
  stack1 = depth0.message;
  stack1 = helpers['if'].call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(30, program30, data)});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n\n    <div id=\"quota-message-container\" style=\"display: none\">\n        <div id=\"quota-message\" class=\"errormessage\">\n            ";
  foundHelper = helpers.local;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{},inverse:self.noop,fn:self.program(32, program32, data)}); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(32, program32, data)}); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n        </div>\n    </div>\n</div>\n\n<div id=\"";
  foundHelper = helpers.id;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.id; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "-datasets\" class=\"history-datasets-list\"></div>\n\n<div class=\"infomessagesmall\" id=\"emptyHistoryMessage\" style=\"display: none;\">\n    ";
  foundHelper = helpers.local;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{},inverse:self.noop,fn:self.program(34, program34, data)}); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(34, program34, data)}); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n</div>";
  return buffer;});
})();