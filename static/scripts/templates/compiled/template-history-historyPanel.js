(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-history-historyPanel'] = template(function (Handlebars,depth0,helpers,partials,data) {
  helpers = helpers || Handlebars.helpers;
  var buffer = "", stack1, foundHelper, functionType="function", escapeExpression=this.escapeExpression, self=this, blockHelperMissing=helpers.blockHelperMissing;

function program1(depth0,data) {
  
  var buffer = "", stack1, foundHelper;
  buffer += "\n            <div id=\"history-name\" style=\"margin-right: 50px;\" class=\"tooltip editable-text\"\n                title=\"Click to rename history\">";
  foundHelper = helpers.name;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.name; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "</div>\n        ";
  return buffer;}

function program3(depth0,data) {
  
  
  return "refresh";}

function program5(depth0,data) {
  
  
  return "collapse all";}

function program7(depth0,data) {
  
  var buffer = "", stack1, foundHelper;
  buffer += "\n        <a id=\"history-tag\" title=\"";
  foundHelper = helpers.local;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{},inverse:self.noop,fn:self.program(8, program8, data)}); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(8, program8, data)}); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\"\n            class=\"icon-button tags tooltip\" target=\"galaxy_main\" href=\"javascript:void(0)\"></a>\n        <a id=\"history-annotate\" title=\"";
  foundHelper = helpers.local;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{},inverse:self.noop,fn:self.program(10, program10, data)}); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(10, program10, data)}); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\"\n            class=\"icon-button annotate tooltip\" target=\"galaxy_main\" href=\"javascript:void(0)\"></a>\n        ";
  return buffer;}
function program8(depth0,data) {
  
  
  return "Edit history tags";}

function program10(depth0,data) {
  
  
  return "Edit history annotation";}

function program12(depth0,data) {
  
  var buffer = "", stack1, foundHelper;
  buffer += "\n    <a href=\"";
  stack1 = depth0.urls;
  stack1 = stack1 == null || stack1 === false ? stack1 : stack1.hide_deleted;
  stack1 = typeof stack1 === functionType ? stack1() : stack1;
  buffer += escapeExpression(stack1) + "\">";
  foundHelper = helpers.local;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{},inverse:self.noop,fn:self.program(13, program13, data)}); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(13, program13, data)}); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "</a>\n    ";
  return buffer;}
function program13(depth0,data) {
  
  
  return "hide deleted";}

function program15(depth0,data) {
  
  var buffer = "", stack1, foundHelper;
  buffer += "\n    <a href=\"";
  stack1 = depth0.urls;
  stack1 = stack1 == null || stack1 === false ? stack1 : stack1.hide_hidden;
  stack1 = typeof stack1 === functionType ? stack1() : stack1;
  buffer += escapeExpression(stack1) + "\">";
  foundHelper = helpers.local;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{},inverse:self.noop,fn:self.program(16, program16, data)}); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(16, program16, data)}); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "</a>\n    ";
  return buffer;}
function program16(depth0,data) {
  
  
  return "hide hidden";}

function program18(depth0,data) {
  
  var buffer = "", stack1, foundHelper;
  buffer += "\n";
  foundHelper = helpers.warningmessagesmall;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{},inverse:self.noop,fn:self.program(19, program19, data)}); }
  else { stack1 = depth0.warningmessagesmall; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  if (!helpers.warningmessagesmall) { stack1 = blockHelperMissing.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(19, program19, data)}); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n";
  return buffer;}
function program19(depth0,data) {
  
  var stack1, foundHelper;
  foundHelper = helpers.local;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{},inverse:self.noop,fn:self.program(20, program20, data)}); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(20, program20, data)}); }
  if(stack1 || stack1 === 0) { return stack1; }
  else { return ''; }}
function program20(depth0,data) {
  
  
  return "You are currently viewing a deleted history!";}

function program22(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n    <div id=\"history-tag-area\" style=\"display: none\">\n        <strong>Tags:</strong>\n        <div class=\"tag-elt\"></div>\n    </div>\n\n    <div id=\"history-annotation-area\" style=\"display: none\">\n        <strong>Annotation / Notes:</strong>\n        <div id=\"history-annotation-container\">\n        <div id=\"history-annotation\" class=\"tooltip editable-text\" title=\"Click to edit annotation\">\n            ";
  stack1 = depth0.annotation;
  stack1 = helpers['if'].call(depth0, stack1, {hash:{},inverse:self.program(25, program25, data),fn:self.program(23, program23, data)});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n        </div>\n        </div>\n    </div>\n    ";
  return buffer;}
function program23(depth0,data) {
  
  var buffer = "", stack1, foundHelper;
  buffer += "\n                ";
  foundHelper = helpers.annotation;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.annotation; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "\n            ";
  return buffer;}

function program25(depth0,data) {
  
  
  return "\n                <em>Describe or add notes to history</em>\n            ";}

function program27(depth0,data) {
  
  var buffer = "", stack1, foundHelper;
  buffer += "\n<div id=\"message-container\">\n    <div class=\"";
  foundHelper = helpers.status;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.status; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "message\">\n    ";
  foundHelper = helpers.message;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.message; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "\n    </div><br />\n</div>\n";
  return buffer;}

function program29(depth0,data) {
  
  
  return "\n    <div id=\"quota-message\" class=\"errormessage\">\n        You are over your disk quota.  Tool execution is on hold until your disk usage drops below your allocated quota.\n    </div>\n    <br/>\n    ";}

function program31(depth0,data) {
  
  
  return "Your history is empty. Click 'Get Data' on the left pane to start";}

  buffer += "\n<div id=\"history-name-area\" class=\"historyLinks\">\n    <div id=\"history-name-container\" style=\"position: relative;\">\n        ";
  buffer += "\n        <div id=\"history-size\" style=\"position: absolute; top: 3px; right: 0px;\">";
  foundHelper = helpers.nice_size;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.nice_size; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "</div>\n        ";
  stack1 = depth0.user;
  stack1 = helpers['if'].call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(1, program1, data)});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n    </div>                     \n</div>\n<div style=\"clear: both;\"></div>\n\n<div id=\"top-links\" class=\"historyLinks\">\n    <a title=\"";
  foundHelper = helpers.local;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{},inverse:self.noop,fn:self.program(3, program3, data)}); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(3, program3, data)}); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\" class=\"icon-button arrow-circle tooltip\" href=\"";
  stack1 = depth0.urls;
  stack1 = stack1 == null || stack1 === false ? stack1 : stack1.base;
  stack1 = typeof stack1 === functionType ? stack1() : stack1;
  buffer += escapeExpression(stack1) + "\"></a>\n    <a title='";
  foundHelper = helpers.local;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{},inverse:self.noop,fn:self.program(5, program5, data)}); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(5, program5, data)}); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "' id=\"history-collapse-all\"\n        class='icon-button toggle tooltip' href='javascript:void(0);'></a>\n    <div style=\"width: 40px; float: right; white-space: nowrap;\">\n        ";
  stack1 = depth0.user;
  stack1 = helpers['if'].call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(7, program7, data)});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n    </div>\n</div>\n<div style=\"clear: both;\"></div>\n\n";
  buffer += "\n<div class=\"historyLinks\">\n    ";
  stack1 = depth0.show_deleted;
  stack1 = helpers['if'].call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(12, program12, data)});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n    ";
  stack1 = depth0.show_hidden;
  stack1 = helpers['if'].call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(15, program15, data)});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n</div>\n\n";
  stack1 = depth0.deleted;
  stack1 = helpers['if'].call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(18, program18, data)});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n\n";
  buffer += "\n";
  buffer += "\n<div style=\"margin: 0px 5px 10px 5px\">\n\n    ";
  stack1 = depth0.user;
  stack1 = helpers['if'].call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(22, program22, data)});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n</div>\n\n";
  stack1 = depth0.message;
  stack1 = helpers['if'].call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(27, program27, data)});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n\n<div id=\"quota-message-container\">\n    ";
  stack1 = depth0.over_quota;
  stack1 = helpers['if'].call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(29, program29, data)});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n</div>\n\n<div id=\"";
  foundHelper = helpers.id;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.id; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "-datasets\" class=\"history-datasets-list\"></div>\n\n<div class=\"infomessagesmall\" id=\"emptyHistoryMessage\" style=\"display: none;\">\n    ";
  foundHelper = helpers.local;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{},inverse:self.noop,fn:self.program(31, program31, data)}); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(31, program31, data)}); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n</div>";
  return buffer;});
})();