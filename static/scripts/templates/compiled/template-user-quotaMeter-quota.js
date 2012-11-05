(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-user-quotaMeter-quota'] = template(function (Handlebars,depth0,helpers,partials,data) {
  helpers = helpers || Handlebars.helpers;
  var buffer = "", stack1, foundHelper, functionType="function", escapeExpression=this.escapeExpression;


  buffer += "<div id=\"quota-meter\" class=\"quota-meter progress\">\n    <div id=\"quota-meter-bar\"  class=\"quota-meter-bar bar\" style=\"width: ";
  foundHelper = helpers.quota_percent;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.quota_percent; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "%\"></div>\n    ";
  buffer += "\n    <div id=\"quota-meter-text\" class=\"quota-meter-text\"style=\"top: 6px\">\n        Using ";
  foundHelper = helpers.quota_percent;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.quota_percent; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "%\n    </div>\n</div>";
  return buffer;});
})();