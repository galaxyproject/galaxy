(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-history-historyPanel'] = template(function (Handlebars,depth0,helpers,partials,data) {
  this.compilerInfo = [2,'>= 1.0.0-rc.3'];
helpers = helpers || Handlebars.helpers; data = data || {};
  var buffer = "", stack1, stack2, options, self=this, functionType="function", blockHelperMissing=helpers.blockHelperMissing, escapeExpression=this.escapeExpression;

function program1(depth0,data) {
  
  var buffer = "", stack1, options;
  buffer += "\n            <div id=\"history-name\" class=\"tooltip editable-text\"\n                title=\"";
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
  buffer += "\n            <div id=\"history-name\" class=\"tooltip\"\n                title=\"";
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
  buffer += "\"\n                class=\"icon-button tags tooltip\" target=\"galaxy_main\" href=\"javascript:void(0)\"></a>\n            <a id=\"history-annotate\" title=\"";
  options = {hash:{},inverse:self.noop,fn:self.program(10, program10, data),data:data};
  if (stack1 = helpers.local) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\"\n                class=\"icon-button annotate tooltip\" target=\"galaxy_main\" href=\"javascript:void(0)\"></a>\n            ";
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
  buffer += ":</strong>\n            <div id=\"history-annotation-container\">\n            <div id=\"history-annotation\" class=\"tooltip editable-text\"\n                title=\"";
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
  
  
  return "You are over your disk quota.\n            Tool execution is on hold until your disk usage drops below your allocated quota.";
  }

function program32(depth0,data) {
  
  
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
  buffer += "\n        </div>\n    </div>\n</div>\n\n<div id=\"";
  if (stack2 = helpers.id) { stack2 = stack2.call(depth0, {hash:{},data:data}); }
  else { stack2 = depth0.id; stack2 = typeof stack2 === functionType ? stack2.apply(depth0) : stack2; }
  buffer += escapeExpression(stack2)
    + "-datasets\" class=\"history-datasets-list\"></div>\n\n<div class=\"infomessagesmall\" id=\"emptyHistoryMessage\" style=\"display: none;\">\n    ";
  options = {hash:{},inverse:self.noop,fn:self.program(32, program32, data),data:data};
  if (stack2 = helpers.local) { stack2 = stack2.call(depth0, options); }
  else { stack2 = depth0.local; stack2 = typeof stack2 === functionType ? stack2.apply(depth0) : stack2; }
  if (!helpers.local) { stack2 = blockHelperMissing.call(depth0, stack2, options); }
  if(stack2 || stack2 === 0) { buffer += stack2; }
  buffer += "\n</div>";
  return buffer;
  });
})();