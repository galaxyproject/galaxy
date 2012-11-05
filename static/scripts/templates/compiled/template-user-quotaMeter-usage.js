(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-user-quotaMeter-usage'] = template(function (Handlebars,depth0,helpers,partials,data) {
  helpers = helpers || Handlebars.helpers;
  var buffer = "", stack1, foundHelper, functionType="function", escapeExpression=this.escapeExpression;


  buffer += "\n<div id=\"quota-meter\" class=\"quota-meter\" style=\"background-color: transparent\">\n    <div id=\"quota-meter-text\" class=\"quota-meter-text\" style=\"top: 6px; color: white\">\n        Using ";
  foundHelper = helpers.nice_total_disk_usage;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.nice_total_disk_usage; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "\n    </div>\n</div>";
  return buffer;});
})();