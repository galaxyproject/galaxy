(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-hda-failedMetadata'] = template(function (Handlebars,depth0,helpers,partials,data) {
  this.compilerInfo = [2,'>= 1.0.0-rc.3'];
helpers = helpers || Handlebars.helpers; data = data || {};
  var stack1, options, self=this, functionType="function", blockHelperMissing=helpers.blockHelperMissing, escapeExpression=this.escapeExpression;

function program1(depth0,data) {
  
  var buffer = "", stack1, options;
  buffer += "\n";
  options = {hash:{},inverse:self.noop,fn:self.program(2, program2, data),data:data};
  if (stack1 = helpers.local) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\nYou may be able to <a href=\""
    + escapeExpression(((stack1 = ((stack1 = depth0.urls),stack1 == null || stack1 === false ? stack1 : stack1.edit)),typeof stack1 === functionType ? stack1.apply(depth0) : stack1))
    + "\" target=\"galaxy_main\">set it manually or retry auto-detection</a>.\n";
  return buffer;
  }
function program2(depth0,data) {
  
  
  return "An error occurred setting the metadata for this dataset.";
  }

  options = {hash:{},inverse:self.noop,fn:self.program(1, program1, data),data:data};
  if (stack1 = helpers.warningmessagesmall) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.warningmessagesmall; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.warningmessagesmall) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { return stack1; }
  else { return ''; }
  });
})();