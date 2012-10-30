(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-history-downloadLinks'] = template(function (Handlebars,depth0,helpers,partials,data) {
  helpers = helpers || Handlebars.helpers;
  var stack1, functionType="function", escapeExpression=this.escapeExpression, self=this;

function program1(depth0,data) {
  
  var buffer = "", stack1, foundHelper;
  buffer += "\n";
  buffer += "\n<div popupmenu=\"dataset-";
  foundHelper = helpers.id;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.id; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "-popup\">\n    <a class=\"action-button\" href=\"";
  stack1 = depth0.urls;
  stack1 = stack1 == null || stack1 === false ? stack1 : stack1.download;
  stack1 = typeof stack1 === functionType ? stack1() : stack1;
  buffer += escapeExpression(stack1) + "\">Download Dataset</a>\n    <a>Additional Files</a>\n    ";
  stack1 = depth0.urls;
  stack1 = stack1 == null || stack1 === false ? stack1 : stack1.meta_download;
  stack1 = helpers.each.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(2, program2, data)});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n</div>\n<div style=\"float:left;\" class=\"menubutton split popup\" id=\"dataset-";
  foundHelper = helpers.id;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.id; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "-popup\">\n    <a href=\"";
  stack1 = depth0.urls;
  stack1 = stack1 == null || stack1 === false ? stack1 : stack1.download;
  stack1 = typeof stack1 === functionType ? stack1() : stack1;
  buffer += escapeExpression(stack1) + "\" title=\"Download\" class=\"icon-button disk tooltip\"></a>\n</div>\n";
  return buffer;}
function program2(depth0,data) {
  
  var buffer = "", stack1, foundHelper;
  buffer += "\n    <a class=\"action-button\" href=\"";
  foundHelper = helpers.url;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.url; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "\">Download ";
  foundHelper = helpers.file_type;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.file_type; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "</a>\n    ";
  return buffer;}

function program4(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n";
  buffer += "\n<a href=\"";
  stack1 = depth0.urls;
  stack1 = stack1 == null || stack1 === false ? stack1 : stack1.download;
  stack1 = typeof stack1 === functionType ? stack1() : stack1;
  buffer += escapeExpression(stack1) + "\" title=\"Download\" class=\"icon-button disk tooltip\"></a>\n";
  return buffer;}

  stack1 = depth0.urls;
  stack1 = stack1 == null || stack1 === false ? stack1 : stack1.meta_download;
  stack1 = helpers['if'].call(depth0, stack1, {hash:{},inverse:self.program(4, program4, data),fn:self.program(1, program1, data)});
  if(stack1 || stack1 === 0) { return stack1; }
  else { return ''; }});
})();