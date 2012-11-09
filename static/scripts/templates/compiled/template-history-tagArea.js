(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-history-tagArea'] = template(function (Handlebars,depth0,helpers,partials,data) {
  helpers = helpers || Handlebars.helpers;
  var buffer = "", stack1, foundHelper, self=this, functionType="function", blockHelperMissing=helpers.blockHelperMissing;

function program1(depth0,data) {
  
  
  return "Tags";}

  buffer += "\n<div class=\"tag-area\" style=\"display: none;\">\n    <strong>";
  foundHelper = helpers.local;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{},inverse:self.noop,fn:self.program(1, program1, data)}); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(1, program1, data)}); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += ":</strong>\n    <div class=\"tag-elt\">\n    </div>\n</div>";
  return buffer;});
})();