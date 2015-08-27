this["Handlebars"] = this["Handlebars"] || {};
this["Handlebars"]["templates"] = this["Handlebars"]["templates"] || {};

this["Handlebars"]["templates"]["tool_search"] = Handlebars.template({"compiler":[6,">= 2.0.0-beta.1"],"main":function(depth0,helpers,partials,data) {
    var helper, alias1=helpers.helperMissing, alias2="function", alias3=this.escapeExpression;

  return "<input type=\"text\" name=\"query\" placeholder=\""
    + alias3(((helper = (helper = helpers.search_hint_string || (depth0 != null ? depth0.search_hint_string : depth0)) != null ? helper : alias1),(typeof helper === alias2 ? helper.call(depth0,{"name":"search_hint_string","hash":{},"data":data}) : helper)))
    + "\" id=\"tool-search-query\" autocomplete=\"off\" class=\"search-query parent-width\" />\n<a id=\"search-clear-btn\" title=\"clear search (esc)\"> </a>\n<img src=\""
    + alias3(((helper = (helper = helpers.spinner_url || (depth0 != null ? depth0.spinner_url : depth0)) != null ? helper : alias1),(typeof helper === alias2 ? helper.call(depth0,{"name":"spinner_url","hash":{},"data":data}) : helper)))
    + "\" id=\"search-spinner\" class=\"search-spinner\"/>\n";
},"useData":true});