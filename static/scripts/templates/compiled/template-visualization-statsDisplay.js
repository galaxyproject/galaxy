(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-visualization-statsDisplay'] = template(function (Handlebars,depth0,helpers,partials,data) {
  helpers = helpers || Handlebars.helpers;
  var buffer = "", stack1, stack2, foundHelper, tmp1, self=this, functionType="function", helperMissing=helpers.helperMissing, undef=void 0, escapeExpression=this.escapeExpression;

function program1(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n        <tr><td>";
  foundHelper = helpers.name;
  stack1 = foundHelper || depth0.name;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "name", { hash: {} }); }
  buffer += escapeExpression(stack1) + "</td><td>";
  foundHelper = helpers.xval;
  stack1 = foundHelper || depth0.xval;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "xval", { hash: {} }); }
  buffer += escapeExpression(stack1) + "</td><td>";
  foundHelper = helpers.yval;
  stack1 = foundHelper || depth0.yval;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "yval", { hash: {} }); }
  buffer += escapeExpression(stack1) + "</td></tr>\n        </tr>\n        ";
  return buffer;}

  buffer += "<p class=\"help-text\">By column:</p>\n    <table id=\"chart-stats-table\">\n        <thead><th></th><th>X</th><th>Y</th></thead>\n        ";
  foundHelper = helpers.stats;
  stack1 = foundHelper || depth0.stats;
  stack2 = helpers.each;
  tmp1 = self.program(1, program1, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  stack1 = stack2.call(depth0, stack1, tmp1);
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n    </table>";
  return buffer;});
})();