(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-user-quotaMeter-quota'] = template(function (Handlebars,depth0,helpers,partials,data) {
  helpers = helpers || Handlebars.helpers;
  var buffer = "", stack1, stack2, foundHelper, tmp1, self=this, functionType="function", helperMissing=helpers.helperMissing, undef=void 0, escapeExpression=this.escapeExpression, blockHelperMissing=helpers.blockHelperMissing;

function program1(depth0,data) {
  
  var buffer = "", stack1;
  buffer += " title=\"Using ";
  foundHelper = helpers.nice_total_disk_usage;
  stack1 = foundHelper || depth0.nice_total_disk_usage;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "nice_total_disk_usage", { hash: {} }); }
  buffer += escapeExpression(stack1) + "\"";
  return buffer;}

function program3(depth0,data) {
  
  
  return "Using";}

  buffer += "<div id=\"quota-meter\" class=\"quota-meter progress\">\n    <div id=\"quota-meter-bar\"  class=\"quota-meter-bar bar\" style=\"width: ";
  foundHelper = helpers.quota_percent;
  stack1 = foundHelper || depth0.quota_percent;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "quota_percent", { hash: {} }); }
  buffer += escapeExpression(stack1) + "%\"></div>\n    ";
  buffer += "\n    <div id=\"quota-meter-text\" class=\"quota-meter-text tooltip\"\n        style=\"top: 6px\"";
  foundHelper = helpers.nice_total_disk_usage;
  stack1 = foundHelper || depth0.nice_total_disk_usage;
  stack2 = helpers['if'];
  tmp1 = self.program(1, program1, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  stack1 = stack2.call(depth0, stack1, tmp1);
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += ">\n        ";
  foundHelper = helpers.local;
  stack1 = foundHelper || depth0.local;
  tmp1 = self.program(3, program3, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  if(foundHelper && typeof stack1 === functionType) { stack1 = stack1.call(depth0, tmp1); }
  else { stack1 = blockHelperMissing.call(depth0, stack1, tmp1); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += " ";
  foundHelper = helpers.quota_percent;
  stack1 = foundHelper || depth0.quota_percent;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "quota_percent", { hash: {} }); }
  buffer += escapeExpression(stack1) + "%\n    </div>\n</div>";
  return buffer;});
})();