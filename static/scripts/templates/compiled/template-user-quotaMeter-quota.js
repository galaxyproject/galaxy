(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-user-quotaMeter-quota'] = template(function (Handlebars,depth0,helpers,partials,data) {
  this.compilerInfo = [2,'>= 1.0.0-rc.3'];
helpers = helpers || Handlebars.helpers; data = data || {};
  var buffer = "", stack1, options, functionType="function", escapeExpression=this.escapeExpression, self=this, blockHelperMissing=helpers.blockHelperMissing;

function program1(depth0,data) {
  
  
  return "Using";
  }

  buffer += "<div id=\"quota-meter\" class=\"quota-meter progress\">\n    <div id=\"quota-meter-bar\"  class=\"quota-meter-bar bar\" style=\"width: ";
  if (stack1 = helpers.quota_percent) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.quota_percent; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "%\"></div>\n    "
    + "\n    <div id=\"quota-meter-text\" class=\"quota-meter-text\"style=\"top: 6px\">\n        ";
  options = {hash:{},inverse:self.noop,fn:self.program(1, program1, data),data:data};
  if (stack1 = helpers.local) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += " ";
  if (stack1 = helpers.quota_percent) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.quota_percent; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "%\n    </div>\n</div>";
  return buffer;
  });
})();