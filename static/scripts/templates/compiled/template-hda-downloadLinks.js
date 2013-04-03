(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-hda-downloadLinks'] = template(function (Handlebars,depth0,helpers,partials,data) {
  this.compilerInfo = [2,'>= 1.0.0-rc.3'];
helpers = helpers || Handlebars.helpers; data = data || {};
  var stack1, stack2, functionType="function", escapeExpression=this.escapeExpression, self=this, blockHelperMissing=helpers.blockHelperMissing;

function program1(depth0,data) {
  
  var buffer = "", stack1, stack2, options;
  buffer += "\n"
    + "\n<div popupmenu=\"dataset-";
  if (stack1 = helpers.id) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.id; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "-popup\">\n    <a class=\"action-button\" href=\""
    + escapeExpression(((stack1 = ((stack1 = depth0.urls),stack1 == null || stack1 === false ? stack1 : stack1.download)),typeof stack1 === functionType ? stack1.apply(depth0) : stack1))
    + "\">";
  options = {hash:{},inverse:self.noop,fn:self.program(2, program2, data),data:data};
  if (stack2 = helpers.local) { stack2 = stack2.call(depth0, options); }
  else { stack2 = depth0.local; stack2 = typeof stack2 === functionType ? stack2.apply(depth0) : stack2; }
  if (!helpers.local) { stack2 = blockHelperMissing.call(depth0, stack2, options); }
  if(stack2 || stack2 === 0) { buffer += stack2; }
  buffer += "</a>\n    <a>";
  options = {hash:{},inverse:self.noop,fn:self.program(4, program4, data),data:data};
  if (stack2 = helpers.local) { stack2 = stack2.call(depth0, options); }
  else { stack2 = depth0.local; stack2 = typeof stack2 === functionType ? stack2.apply(depth0) : stack2; }
  if (!helpers.local) { stack2 = blockHelperMissing.call(depth0, stack2, options); }
  if(stack2 || stack2 === 0) { buffer += stack2; }
  buffer += "</a>\n    ";
  stack2 = helpers.each.call(depth0, ((stack1 = depth0.urls),stack1 == null || stack1 === false ? stack1 : stack1.meta_download), {hash:{},inverse:self.noop,fn:self.program(6, program6, data),data:data});
  if(stack2 || stack2 === 0) { buffer += stack2; }
  buffer += "\n</div>\n<div style=\"float:left;\" class=\"menubutton split popup\" id=\"dataset-";
  if (stack2 = helpers.id) { stack2 = stack2.call(depth0, {hash:{},data:data}); }
  else { stack2 = depth0.id; stack2 = typeof stack2 === functionType ? stack2.apply(depth0) : stack2; }
  buffer += escapeExpression(stack2)
    + "-popup\">\n    <a href=\""
    + escapeExpression(((stack1 = ((stack1 = depth0.urls),stack1 == null || stack1 === false ? stack1 : stack1.download)),typeof stack1 === functionType ? stack1.apply(depth0) : stack1))
    + "\" title=\"";
  options = {hash:{},inverse:self.noop,fn:self.program(7, program7, data),data:data};
  if (stack2 = helpers.local) { stack2 = stack2.call(depth0, options); }
  else { stack2 = depth0.local; stack2 = typeof stack2 === functionType ? stack2.apply(depth0) : stack2; }
  if (!helpers.local) { stack2 = blockHelperMissing.call(depth0, stack2, options); }
  if(stack2 || stack2 === 0) { buffer += stack2; }
  buffer += "\" class=\"icon-button disk tooltip\"></a>\n</div>\n";
  return buffer;
  }
function program2(depth0,data) {
  
  
  return "Download Dataset";
  }

function program4(depth0,data) {
  
  
  return "Additional Files";
  }

function program6(depth0,data) {
  
  var buffer = "", stack1, options;
  buffer += "\n    <a class=\"action-button\" href=\"";
  if (stack1 = helpers.url) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.url; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "\">";
  options = {hash:{},inverse:self.noop,fn:self.program(7, program7, data),data:data};
  if (stack1 = helpers.local) { stack1 = stack1.call(depth0, options); }
  else { stack1 = depth0.local; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  if (!helpers.local) { stack1 = blockHelperMissing.call(depth0, stack1, options); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += " ";
  if (stack1 = helpers.file_type) { stack1 = stack1.call(depth0, {hash:{},data:data}); }
  else { stack1 = depth0.file_type; stack1 = typeof stack1 === functionType ? stack1.apply(depth0) : stack1; }
  buffer += escapeExpression(stack1)
    + "</a>\n    ";
  return buffer;
  }
function program7(depth0,data) {
  
  
  return "Download";
  }

function program9(depth0,data) {
  
  var buffer = "", stack1, stack2, options;
  buffer += "\n"
    + "\n<a href=\""
    + escapeExpression(((stack1 = ((stack1 = depth0.urls),stack1 == null || stack1 === false ? stack1 : stack1.download)),typeof stack1 === functionType ? stack1.apply(depth0) : stack1))
    + "\" title=\"";
  options = {hash:{},inverse:self.noop,fn:self.program(7, program7, data),data:data};
  if (stack2 = helpers.local) { stack2 = stack2.call(depth0, options); }
  else { stack2 = depth0.local; stack2 = typeof stack2 === functionType ? stack2.apply(depth0) : stack2; }
  if (!helpers.local) { stack2 = blockHelperMissing.call(depth0, stack2, options); }
  if(stack2 || stack2 === 0) { buffer += stack2; }
  buffer += "\" class=\"icon-button disk tooltip\"></a>\n";
  return buffer;
  }

  stack2 = helpers['if'].call(depth0, ((stack1 = depth0.urls),stack1 == null || stack1 === false ? stack1 : stack1.meta_download), {hash:{},inverse:self.program(9, program9, data),fn:self.program(1, program1, data),data:data});
  if(stack2 || stack2 === 0) { return stack2; }
  else { return ''; }
  });
})();