(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['tool_search'] = template(function (Handlebars,depth0,helpers,partials,data) {
  helpers = helpers || Handlebars.helpers;
  var buffer = "", stack1, foundHelper, self=this, functionType="function", helperMissing=helpers.helperMissing, undef=void 0, escapeExpression=this.escapeExpression;


  buffer += "<input type=\"text\" name=\"query\" value=\"";
  foundHelper = helpers.search_hint_string;
  stack1 = foundHelper || depth0.search_hint_string;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "search_hint_string", { hash: {} }); }
  buffer += escapeExpression(stack1) + "\" id=\"tool-search-query\" autocomplete=\"off\" class=\"search-query parent-width\" />\n<a id=\"search-clear-btn\" class=\"tooltip\" title=\"clear search (esc)\"> </a>\n<img src=\"";
  foundHelper = helpers.spinner_url;
  stack1 = foundHelper || depth0.spinner_url;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "spinner_url", { hash: {} }); }
  buffer += escapeExpression(stack1) + "\" id=\"search-spinner\" class=\"search-spinner\"/>";
  return buffer;});
})();