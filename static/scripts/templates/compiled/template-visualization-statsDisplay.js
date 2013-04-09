(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-visualization-statsDisplay'] = template(function (Handlebars,depth0,helpers,partials,data) {
  this.compilerInfo = [2,'>= 1.0.0-rc.3'];
helpers = helpers || Handlebars.helpers; data = data || {};
  var buffer = "", stack1, functionType="function", escapeExpression=this.escapeExpression, self=this;

function program1(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n        <tr><td>";
  if (stack1 = helpers.name) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.name; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "</td><td>";
  if (stack1 = helpers.xval) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.xval; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "</td><td>";
  if (stack1 = helpers.yval) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.yval; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "</td></tr>\n        </tr>\n        ";
  return buffer;
  }

  buffer += "<p class=\"help-text\">By column:</p>\n    <table id=\"chart-stats-table\">\n        <thead><th></th><th>X</th><th>Y</th></thead>\n        ";
  stack1 = helpers.each.call(depth0, depth0.stats, {hash:{},inverse:self.noop,fn:self.program(1, program1, data),data:data});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n    </table>";
  return buffer;
  });
})();