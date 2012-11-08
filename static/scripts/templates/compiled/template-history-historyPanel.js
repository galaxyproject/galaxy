(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-history-historyPanel'] = template(function (Handlebars,depth0,helpers,partials,data) {
  helpers = helpers || Handlebars.helpers;
  var buffer = "", stack1, foundHelper, functionType="function", escapeExpression=this.escapeExpression, self=this, blockHelperMissing=helpers.blockHelperMissing;

function program1(depth0,data) {
  
  var buffer = "", stack1, foundHelper;
  buffer += "\n            <div id=\"history-name\" class=\"tooltip editable-text\"\n                title=\"Click to rename history\">";
  foundHelper = helpers.name;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.name; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "</div>\n            ";
  return buffer;}

function program3(depth0,data) {
  
  var buffer = "", stack1, foundHelper;
  buffer += "\n            <div id=\"history-name\" class=\"tooltip\"\n                title=\"You must be logged in to edit your history name\">";
  foundHelper = helpers.name;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.name; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "</div>\n            ";
  return buffer;}

function program5(depth0,data) {
  
  
  return "Click to see more actions";}

function program7(depth0,data) {
  
  var buffer = "", stack1, foundHelper;
  buffer += "\n        <div id=\"history-secondary-links\" style=\"float: right;\">\n            <a id=\"history-tag\" title=\"";
  foundHelper = helpers.local;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{},inverse:self.noop,fn:self.program(8, program8, data)}); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(8, program8, data)}); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\"\n                class=\"icon-button tags tooltip\" target=\"galaxy_main\" href=\"javascript:void(0)\"></a>\n            <a id=\"history-annotate\" title=\"";
  foundHelper = helpers.local;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{},inverse:self.noop,fn:self.program(10, program10, data)}); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(10, program10, data)}); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\"\n                class=\"icon-button annotate tooltip\" target=\"galaxy_main\" href=\"javascript:void(0)\"></a>\n        </div>\n        ";
  return buffer;}
function program8(depth0,data) {
  
  
  return "Edit history tags";}

function program10(depth0,data) {
  
  
  return "Edit history annotation";}

function program12(depth0,data) {
  
  var buffer = "", stack1, foundHelper;
  buffer += "\n    ";
  foundHelper = helpers.warningmessagesmall;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{},inverse:self.noop,fn:self.program(13, program13, data)}); }
  else { stack1 = depth0.warningmessagesmall; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  if (!helpers.warningmessagesmall) { stack1 = blockHelperMissing.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(13, program13, data)}); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n    ";
  return buffer;}
function program13(depth0,data) {
  
  var stack1, foundHelper;
  foundHelper = helpers.local;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{},inverse:self.noop,fn:self.program(14, program14, data)}); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(14, program14, data)}); }
  if(stack1 || stack1 === 0) { return stack1; }
  else { return ''; }}
function program14(depth0,data) {
  
  
  return "You are currently viewing a deleted history!";}

function program16(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n    <div id=\"history-tag-annotation\">\n\n        <div id=\"history-tag-area\" style=\"display: none\">\n            <strong>Tags:</strong>\n            <div class=\"tag-elt\"></div>\n        </div>\n\n        <div id=\"history-annotation-area\" style=\"display: none\">\n            <strong>Annotation / Notes:</strong>\n            <div id=\"history-annotation-container\">\n            <div id=\"history-annotation\" class=\"tooltip editable-text\" title=\"Click to edit annotation\">\n                ";
  stack1 = depth0.annotation;
  stack1 = helpers['if'].call(depth0, stack1, {hash:{},inverse:self.program(19, program19, data),fn:self.program(17, program17, data)});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n            </div>\n            </div>\n        </div>\n    </div>\n    ";
  return buffer;}
function program17(depth0,data) {
  
  var buffer = "", stack1, foundHelper;
  buffer += "\n                    ";
  foundHelper = helpers.annotation;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.annotation; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "\n                ";
  return buffer;}

function program19(depth0,data) {
  
  
  return "\n                    <em>Describe or add notes to history</em>\n                ";}

function program21(depth0,data) {
  
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

function program23(depth0,data) {
  
  
  return "Your history is empty. Click 'Get Data' on the left pane to start";}

  buffer += "\n<div id=\"history-controls\">\n    <div id=\"history-title-area\" class=\"historyLinks\">\n\n        <div id=\"history-name-container\" style=\"float: left;\">\n            ";
  buffer += "\n            ";
  stack1 = depth0.user;
  stack1 = stack1 == null || stack1 === false ? stack1 : stack1.email;
  stack1 = helpers['if'].call(depth0, stack1, {hash:{},inverse:self.program(3, program3, data),fn:self.program(1, program1, data)});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n        </div>\n\n        <a id=\"history-action-popup\" class=\"tooltip\" title=\"";
  foundHelper = helpers.local;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{},inverse:self.noop,fn:self.program(5, program5, data)}); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(5, program5, data)}); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\"\n            href=\"javascript:void(0);\" style=\"float: right;\">\n            <span class=\"ficon cog large\"></span>\n        </a>\n        <div style=\"clear: both;\"></div>\n    </div>\n\n    <div id=\"history-subtitle-area\">\n        <div id=\"history-size\" style=\"float:left;\">";
  foundHelper = helpers.nice_size;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.nice_size; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "</div>\n        ";
  stack1 = depth0.user;
  stack1 = stack1 == null || stack1 === false ? stack1 : stack1.email;
  stack1 = helpers['if'].call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(7, program7, data)});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n        <div style=\"clear: both;\"></div>\n    </div>\n\n    ";
  stack1 = depth0.deleted;
  stack1 = helpers['if'].call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(12, program12, data)});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n\n    ";
  buffer += "\n    ";
  buffer += "\n    ";
  stack1 = depth0.user;
  stack1 = stack1 == null || stack1 === false ? stack1 : stack1.email;
  stack1 = helpers['if'].call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(16, program16, data)});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n\n    ";
  stack1 = depth0.message;
  stack1 = helpers['if'].call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(21, program21, data)});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n\n    <div id=\"quota-message-container\" style=\"display: none\">\n        <div id=\"quota-message\" class=\"errormessage\">\n            You are over your disk quota.  Tool execution is on hold until your disk usage drops below your allocated quota.\n        </div>\n    </div>\n</div>\n\n<div id=\"";
  foundHelper = helpers.id;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.id; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "-datasets\" class=\"history-datasets-list\"></div>\n\n<div class=\"infomessagesmall\" id=\"emptyHistoryMessage\" style=\"display: none;\">\n    ";
  foundHelper = helpers.local;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{},inverse:self.noop,fn:self.program(23, program23, data)}); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(23, program23, data)}); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n</div>";
  return buffer;});
})();