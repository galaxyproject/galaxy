(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-visualization-chartSettings'] = template(function (Handlebars,depth0,helpers,partials,data) {
  helpers = helpers || Handlebars.helpers;
  var buffer = "", stack1, foundHelper, functionType="function", escapeExpression=this.escapeExpression, self=this;

function program1(depth0,data) {
  
  
  return "checked";}

  buffer += "<p class=\"help-text\">\n        Use the following controls to how the chart is displayed.\n        The slide controls can be moved by the mouse or, if the 'handle' is in focus, your keyboard's arrow keys.\n        Move the focus between controls by using the tab or shift+tab keys on your keyboard.\n        Use the 'Draw' button to render (or re-render) the chart with the current settings.\n    </p>\n        \n    <div id=\"maxDataPoints\" class=\"form-input numeric-slider-input\">\n        <label for=\"maxDataPoints\">Maximum data points allowed on graph: </label>\n        <div class=\"slider-output\">";
  foundHelper = helpers.maxDataPoints;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.maxDataPoints; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "</div>\n        <div style=\"clear: both;\"></div>\n        <div class=\"slider\"></div>\n        <p class=\"form-help help-text-small\">\n            Change the maximum number of data points displayable on this graph (higher values will\n            load significantly slower)\n        </p>\n    </div>\n\n    <div id=\"datapointSize\" class=\"form-input numeric-slider-input\">\n        <label for=\"datapointSize\">Size of data point: </label>\n        <div class=\"slider-output\">";
  foundHelper = helpers.datapointSize;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.datapointSize; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "</div>\n        <div class=\"slider\"></div>\n        <p class=\"form-help help-text-small\">\n            Size of the graphic representation of each data point\n        </p>\n    </div>\n\n    <div id=\"entryAnimDuration\" class=\"form-input checkbox-input\">\n        <label for=\"animated\">Animate graph transitions?: </label>\n        <input type=\"checkbox\" id=\"animated\" class=\"checkbox control\" value=\"";
  stack1 = depth0.entryAnimDuration;
  stack1 = helpers['if'].call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(1, program1, data)});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\" />\n        <p class=\"form-help help-text-small\">\n            Uncheck this to disable the animations used on the graph\n        </p>\n    </div>\n\n    <div id=\"width\" class=\"form-input numeric-slider-input\">\n        <label for=\"width\">Graph width: </label>\n        <div class=\"slider-output\">";
  foundHelper = helpers.width;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.width; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "</div>\n        <div class=\"slider\"></div>\n        <p class=\"form-help help-text-small\">\n            (not including graph margins and axes)\n        </p>\n    </div>\n\n    <div id=\"height\" class=\"form-input numeric-slider-input\">\n        <label for=\"height\">Graph height: </label>\n        <div class=\"slider-output\">";
  foundHelper = helpers.height;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.height; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "</div>\n        <div class=\"slider\"></div>\n        <p class=\"form-help help-text-small\">\n            (not including graph margins and axes)\n        </p>\n    </div>\n\n    <div id=\"X-axis-label\"class=\"text-input form-input\">\n        <label for=\"X-axis-label\">Re-label the X axis: </label>\n        <input type=\"text\" name=\"X-axis-label\" id=\"X-axis-label\" value=\"";
  foundHelper = helpers.xLabel;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.xLabel; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "\" />\n        <p class=\"form-help help-text-small\"></p>\n    </div>\n\n    <div id=\"Y-axis-label\" class=\"text-input form-input\">\n        <label for=\"Y-axis-label\">Re-label the Y axis: </label>\n        <input type=\"text\" name=\"Y-axis-label\" id=\"Y-axis-label\" value=\"";
  foundHelper = helpers.yLabel;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.yLabel; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "\" />\n        <p class=\"form-help help-text-small\"></p>\n    </div>\n\n    <input id=\"render-button\" type=\"button\" value=\"Draw\" />";
  return buffer;});
})();