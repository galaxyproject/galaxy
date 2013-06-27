(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-hda-failedMetadata'] = template(function (Handlebars,depth0,helpers,partials,data) {
  helpers = helpers || Handlebars.helpers;
  var stack1, foundHelper, tmp1, self=this, functionType="function", blockHelperMissing=helpers.blockHelperMissing, helperMissing=helpers.helperMissing, undef=void 0, escapeExpression=this.escapeExpression;

function program1(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n";
  foundHelper = helpers.local;
  stack1 = foundHelper || depth0.local;
  tmp1 = self.program(2, program2, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  if(foundHelper && typeof stack1 === functionType) { stack1 = stack1.call(depth0, tmp1); }
  else { stack1 = blockHelperMissing.call(depth0, stack1, tmp1); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\nYou may be able to <a href=\"";
  foundHelper = helpers.urls;
  stack1 = foundHelper || depth0.urls;
  stack1 = (stack1 === null || stack1 === undefined || stack1 === false ? stack1 : stack1.edit);
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "urls.edit", { hash: {} }); }
  buffer += escapeExpression(stack1) + "\" target=\"galaxy_main\">set it manually or retry auto-detection</a>.\n";
  return buffer;}
function program2(depth0,data) {
  
  
  return "An error occurred setting the metadata for this dataset.";}

  foundHelper = helpers.warningmessagesmall;
  stack1 = foundHelper || depth0.warningmessagesmall;
  tmp1 = self.program(1, program1, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  if(foundHelper && typeof stack1 === functionType) { stack1 = stack1.call(depth0, tmp1); }
  else { stack1 = blockHelperMissing.call(depth0, stack1, tmp1); }
  if(stack1 || stack1 === 0) { return stack1; }
  else { return ''; }});
})();