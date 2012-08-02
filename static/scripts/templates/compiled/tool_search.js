(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['tool_search'] = template(function (Handlebars,depth0,helpers,partials,data) {
  helpers = helpers || Handlebars.helpers;
  var buffer = "", stack1, foundHelper, functionType="function", escapeExpression=this.escapeExpression;


  buffer += "<input type=\"text\" name=\"query\" value=\"";
  foundHelper = helpers.search_hint_string;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.search_hint_string; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "\" id=\"tool-search-query\" autocomplete=\"off\" class=\"search-query parent-width\" />\n<a id=\"search-clear-btn\" class=\"icon-button cross-circle tooltip\" title=\"clear search (esc)\"> </a>\n<img src=\"";
  foundHelper = helpers.spinner_url;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.spinner_url; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "\" id=\"search-spinner\" class=\"search-spinner\"/>";
  return buffer;});
})();