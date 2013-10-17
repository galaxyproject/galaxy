(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['tool_search'] = template(function (Handlebars,depth0,helpers,partials,data) {
  this.compilerInfo = [4,'>= 1.0.0'];
helpers = this.merge(helpers, Handlebars.helpers); data = data || {};
  var buffer = "", stack1, functionType="function", escapeExpression=this.escapeExpression;


  buffer += "<input type=\"text\" name=\"query\" value=\"";
  if (stack1 = helpers.search_hint_string) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.search_hint_string; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "\" id=\"tool-search-query\" autocomplete=\"off\" class=\"search-query parent-width\" />\n<a id=\"search-clear-btn\" title=\"clear search (esc)\"> </a>\n<img src=\"";
  if (stack1 = helpers.spinner_url) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.spinner_url; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "\" id=\"search-spinner\" class=\"search-spinner\"/>";
  return buffer;
  });
})();