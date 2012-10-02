(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-visualization-scatterplotControlForm'] = template(function (Handlebars,depth0,helpers,partials,data) {
  helpers = helpers || Handlebars.helpers;
  var buffer = "", stack1, foundHelper, functionType="function", escapeExpression=this.escapeExpression, self=this;

function program1(depth0,data) {
  
  var buffer = "", stack1, foundHelper;
  buffer += "\n            <option value=\"";
  foundHelper = helpers.index;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.index; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "\">";
  foundHelper = helpers.name;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.name; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "</option>\n        ";
  return buffer;}

function program3(depth0,data) {
  
  var buffer = "", stack1, foundHelper;
  buffer += "\n            <option value=\"";
  foundHelper = helpers.index;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.index; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "\">";
  foundHelper = helpers.name;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.name; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "</option>\n        ";
  return buffer;}

  buffer += "\n<div id=\"loading-indicator\" style=\"display: none;\">\n    <img class=\"loading-img\" src=\"";
  foundHelper = helpers.loadingIndicatorImagePath;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.loadingIndicatorImagePath; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "\" />\n    <span class=\"loading-message\"></span>\n</div>\n\n";
  buffer += "\n<div id=\"chart-settings\">\n\n    ";
  buffer += "\n    <div id=\"x-column-input\">\n        <label for=\"\">Data column for X: </label>\n        <select name=\"x-column\">\n        ";
  stack1 = depth0.availableColumns;
  stack1 = helpers.each.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(1, program1, data)});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n        </select>\n    </div>\n    <div id=\"y-column-input\">\n        <label for=\"\">Data column for Y: </label>\n        <select name=\"y-column\">\n        ";
  stack1 = depth0.availableColumns;
  stack1 = helpers.each.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(3, program3, data)});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n        </select>\n    </div>\n    \n    <input id=\"render-button\" type=\"button\" value=\"Draw\" />\n    <div class=\"clear\"></div>\n</div>";
  return buffer;});
})();