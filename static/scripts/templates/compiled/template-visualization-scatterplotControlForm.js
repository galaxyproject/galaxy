(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-visualization-scatterplotControlForm'] = template(function (Handlebars,depth0,helpers,partials,data) {
  helpers = helpers || Handlebars.helpers;
  var buffer = "", stack1, foundHelper, functionType="function", escapeExpression=this.escapeExpression;


  buffer += "\n\n<div class=\"scatterplot-container chart-container tabbable tabs-left\">\n    ";
  buffer += "\n    <ul class=\"nav nav-tabs\">\n        ";
  buffer += "\n        <li class=\"active\"><a href=\"#data-control\" data-toggle=\"tab\" class=\"tooltip\"\n            title=\"Use this tab to change which data are used\">Data Controls</a></li>\n        <li><a href=\"#chart-control\" data-toggle=\"tab\" class=\"tooltip\"\n            title=\"Use this tab to change how the chart is drawn\">Chart Controls</a></li>\n        <li><a href=\"#stats-display\" data-toggle=\"tab\" class=\"tooltip\"\n            title=\"This tab will display overall statistics for your data\">Statistics</a></li>\n        <li><a href=\"#chart-display\" data-toggle=\"tab\" class=\"tooltip\"\n            title=\"This tab will display the chart\">Chart</a>\n            ";
  buffer += "\n            <div id=\"loading-indicator\" style=\"display: none;\">\n                <img class=\"loading-img\" src=\"";
  foundHelper = helpers.loadingIndicatorImagePath;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.loadingIndicatorImagePath; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "\" />\n                <span class=\"loading-message\">";
  foundHelper = helpers.message;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.message; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "</span>\n            </div>\n        </li>\n    </ul>\n\n    ";
  buffer += "\n    <div class=\"tab-content\">\n        ";
  buffer += "\n        <div id=\"data-control\" class=\"tab-pane active\">\n            ";
  buffer += "\n        </div>\n    \n        ";
  buffer += "\n        <div id=\"chart-control\" class=\"tab-pane\">\n            ";
  buffer += "\n        </div>\n\n        ";
  buffer += "\n        <div id=\"stats-display\" class=\"tab-pane\">\n            ";
  buffer += "\n        </div>\n\n        ";
  buffer += "\n        <div id=\"chart-display\" class=\"tab-pane\">\n            ";
  buffer += "\n        </div>\n\n    </div>";
  buffer += "\n</div>";
  return buffer;});
})();