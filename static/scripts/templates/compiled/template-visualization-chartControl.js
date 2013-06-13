(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-visualization-chartControl'] = template(function (Handlebars,depth0,helpers,partials,data) {
  this.compilerInfo = [2,'>= 1.0.0-rc.3'];
helpers = helpers || Handlebars.helpers; data = data || {};
  var buffer = "", stack1, functionType="function", escapeExpression=this.escapeExpression, self=this;

function program1(depth0,data) {
  
  
  return " checked=\"true\"";
  }

  buffer += "<p class=\"help-text\">\n        Use the following controls to how the chart is displayed.\n        The slide controls can be moved by the mouse or, if the 'handle' is in focus, your keyboard's arrow keys.\n        Move the focus between controls by using the tab or shift+tab keys on your keyboard.\n        Use the 'Draw' button to render (or re-render) the chart with the current settings.\n    </p>\n\n    <div id=\"datapointSize\" class=\"form-input numeric-slider-input\">\n        <label for=\"datapointSize\">Size of data point: </label>\n        <div class=\"slider-output\">";
  if (stack1 = helpers.datapointSize) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.datapointSize; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "</div>\n        <div class=\"slider\"></div>\n        <p class=\"form-help help-text-small\">\n            Size of the graphic representation of each data point\n        </p>\n    </div>\n\n    <div id=\"animDuration\" class=\"form-input checkbox-input\">\n        <label for=\"animate-chart\">Animate chart transitions?: </label>\n        <input type=\"checkbox\" id=\"animate-chart\"\n            class=\"checkbox control\"";
  stack1 = helpers['if'].call(depth0, depth0.animDuration, {hash:{},inverse:self.noop,fn:self.program(1, program1, data),data:data});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += " />\n        <p class=\"form-help help-text-small\">\n            Uncheck this to disable the animations used on the chart\n        </p>\n    </div>\n\n    <div id=\"width\" class=\"form-input numeric-slider-input\">\n        <label for=\"width\">Chart width: </label>\n        <div class=\"slider-output\">";
  if (stack1 = helpers.width) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.width; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "</div>\n        <div class=\"slider\"></div>\n        <p class=\"form-help help-text-small\">\n            (not including chart margins and axes)\n        </p>\n    </div>\n\n    <div id=\"height\" class=\"form-input numeric-slider-input\">\n        <label for=\"height\">Chart height: </label>\n        <div class=\"slider-output\">";
  if (stack1 = helpers.height) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.height; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "</div>\n        <div class=\"slider\"></div>\n        <p class=\"form-help help-text-small\">\n            (not including chart margins and axes)\n        </p>\n    </div>\n\n    <div id=\"X-axis-label\"class=\"text-input form-input\">\n        <label for=\"X-axis-label\">Re-label the X axis: </label>\n        <input type=\"text\" name=\"X-axis-label\" id=\"X-axis-label\" value=\"";
  if (stack1 = helpers.xLabel) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.xLabel; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "\" />\n        <p class=\"form-help help-text-small\"></p>\n    </div>\n\n    <div id=\"Y-axis-label\" class=\"text-input form-input\">\n        <label for=\"Y-axis-label\">Re-label the Y axis: </label>\n        <input type=\"text\" name=\"Y-axis-label\" id=\"Y-axis-label\" value=\"";
  if (stack1 = helpers.yLabel) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.yLabel; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "\" />\n        <p class=\"form-help help-text-small\"></p>\n    </div>\n\n    <input id=\"render-button\" type=\"button\" value=\"Draw\" />";
  return buffer;
  });
})();