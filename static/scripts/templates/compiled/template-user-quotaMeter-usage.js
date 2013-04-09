(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-user-quotaMeter-usage'] = template(function (Handlebars,depth0,helpers,partials,data) {
  this.compilerInfo = [2,'>= 1.0.0-rc.3'];
helpers = helpers || Handlebars.helpers; data = data || {};
  var buffer = "", stack1, options, self=this, functionType="function", blockHelperMissing=helpers.blockHelperMissing, escapeExpression=this.escapeExpression;

function program1(depth0,data) {
  
  
  return "Using";
  }

  buffer += "\n<div id=\"quota-meter\" class=\"quota-meter\" style=\"background-color: transparent\">\n    <div id=\"quota-meter-text\" class=\"quota-meter-text\" style=\"top: 6px; color: white\">\n        ";
  options = {hash:{},inverse:self.noop,fn:self.program(1, program1, data),data:data};
  if (stack1 = helpers.local) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += " ";
  if (stack1 = helpers.nice_total_disk_usage) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.nice_total_disk_usage; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "\n    </div>\n</div>";
  return buffer;
  });
})();