(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-hda-hdaSummary'] = template(function (Handlebars,depth0,helpers,partials,data) {
  this.compilerInfo = [2,'>= 1.0.0-rc.3'];
helpers = helpers || Handlebars.helpers; data = data || {};
  var buffer = "", stack1, functionType="function", escapeExpression=this.escapeExpression, self=this;

function program1(depth0,data) {
  
  var buffer = "", stack1, stack2;
  buffer += "\n        <a class=\"metadata-dbkey\" href=\""
    + escapeExpression(((stack1 = ((stack1 = depth0.urls),stack1 == null || stack1 === false ? stack1 : stack1.edit)),typeof stack1 === functionType ? stack1.apply(depth0) : stack1))
    + "\" target=\"galaxy_main\">";
  if (stack2 = helpers.metadata_dbkey) { stack2 = stack2.call(depth0, {hash:{},data:data}); }
  else { stack2 = depth0.metadata_dbkey; stack2 = typeof stack2 === functionType ? stack2.apply(depth0) : stack2; }
  buffer += escapeExpression(stack2)
    + "</a>\n    ";
  return buffer;
  }

function program3(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n        <span class=\"metadata-dbkey ";
  if (stack1 = helpers.metadata_dbkey) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.metadata_dbkey; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "\">";
  if (stack1 = helpers.metadata_dbkey) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.metadata_dbkey; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "</span>\n    ";
  return buffer;
  }

function program5(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n<div class=\"hda-info\"> ";
  if (stack1 = helpers.misc_info) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.misc_info; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + " </div>\n";
  return buffer;
  }

  buffer += "<div class=\"hda-summary\">\n    ";
  if (stack1 = helpers.misc_blurb) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.misc_blurb; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "<br />\n    format: <span class=\"";
  if (stack1 = helpers.data_type) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.data_type; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "\">";
  if (stack1 = helpers.data_type) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.data_type; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "</span>,\n    database:\n    ";
  stack1 = helpers['if'].call(depth0, depth0.dbkey_unknown_and_editable, {hash:{},inverse:self.program(3, program3, data),fn:self.program(1, program1, data),data:data});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n</div>\n";
  stack1 = helpers['if'].call(depth0, depth0.misc_info, {hash:{},inverse:self.noop,fn:self.program(5, program5, data),data:data});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  return buffer;
  });
})();