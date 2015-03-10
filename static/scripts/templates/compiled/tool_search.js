(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['tool_search'] = template({"compiler":[6,">= 2.0.0-beta.1"],"main":function(depth0,helpers,partials,data) {
  var helper, functionType="function", helperMissing=helpers.helperMissing, escapeExpression=this.escapeExpression;
  return "<input type=\"text\" name=\"query\" value=\""
    + escapeExpression(((helper = (helper = helpers.search_hint_string || (depth0 != null ? depth0.search_hint_string : depth0)) != null ? helper : helperMissing),(typeof helper === functionType ? helper.call(depth0, {"name":"search_hint_string","hash":{},"data":data}) : helper)))
    + "\" id=\"tool-search-query\" autocomplete=\"off\" class=\"search-query parent-width\" />\n<a id=\"search-clear-btn\" title=\"clear search (esc)\"> </a>\n<img src=\""
    + escapeExpression(((helper = (helper = helpers.spinner_url || (depth0 != null ? depth0.spinner_url : depth0)) != null ? helper : helperMissing),(typeof helper === functionType ? helper.call(depth0, {"name":"spinner_url","hash":{},"data":data}) : helper)))
    + "\" id=\"search-spinner\" class=\"search-spinner\"/>";
},"useData":true});
})();