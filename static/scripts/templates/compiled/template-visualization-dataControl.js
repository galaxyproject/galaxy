(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['template-visualization-dataControl'] = template(function (Handlebars,depth0,helpers,partials,data) {
  helpers = helpers || Handlebars.helpers;
  var buffer = "", stack1, stack2, foundHelper, tmp1, self=this, functionType="function", helperMissing=helpers.helperMissing, undef=void 0, escapeExpression=this.escapeExpression;

function program1(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n            <option value=\"";
  foundHelper = helpers.index;
  stack1 = foundHelper || depth0.index;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "index", { hash: {} }); }
  buffer += escapeExpression(stack1) + "\">";
  foundHelper = helpers.name;
  stack1 = foundHelper || depth0.name;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "name", { hash: {} }); }
  buffer += escapeExpression(stack1) + "</option>\n        ";
  return buffer;}

function program3(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n            <option value=\"";
  foundHelper = helpers.index;
  stack1 = foundHelper || depth0.index;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "index", { hash: {} }); }
  buffer += escapeExpression(stack1) + "\">";
  foundHelper = helpers.name;
  stack1 = foundHelper || depth0.name;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "name", { hash: {} }); }
  buffer += escapeExpression(stack1) + "</option>\n        ";
  return buffer;}

function program5(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n            <option value=\"";
  foundHelper = helpers.index;
  stack1 = foundHelper || depth0.index;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "index", { hash: {} }); }
  buffer += escapeExpression(stack1) + "\">";
  foundHelper = helpers.name;
  stack1 = foundHelper || depth0.name;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "name", { hash: {} }); }
  buffer += escapeExpression(stack1) + "</option>\n        ";
  return buffer;}

function program7(depth0,data) {
  
  
  return "checked=\"true\"";}

  buffer += "<p class=\"help-text\">\n        Use the following controls to change the data used by the chart.\n        Use the 'Draw' button to render (or re-render) the chart with the current settings.\n    </p>\n\n    ";
  buffer += "\n    <div class=\"column-select\">\n        <label for=\"X-select\">Data column for X: </label>\n        <select name=\"X\" id=\"X-select\">\n        ";
  foundHelper = helpers.numericColumns;
  stack1 = foundHelper || depth0.numericColumns;
  stack2 = helpers.each;
  tmp1 = self.program(1, program1, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  stack1 = stack2.call(depth0, stack1, tmp1);
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n        </select>\n    </div>\n    <div class=\"column-select\">\n        <label for=\"Y-select\">Data column for Y: </label>\n        <select name=\"Y\" id=\"Y-select\">\n        ";
  foundHelper = helpers.numericColumns;
  stack1 = foundHelper || depth0.numericColumns;
  stack2 = helpers.each;
  tmp1 = self.program(3, program3, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  stack1 = stack2.call(depth0, stack1, tmp1);
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n        </select>\n    </div>\n\n    ";
  buffer += "\n    <div id=\"include-id\">\n        <label for=\"include-id-checkbox\">Include a third column as data point IDs?</label>\n        <input type=\"checkbox\" name=\"include-id\" id=\"include-id-checkbox\" />\n        <p class=\"help-text-small\">\n            These will be displayed (along with the x and y values) when you hover over\n            a data point.\n        </p>\n    </div>\n    <div class=\"column-select\" style=\"display: none\">\n        <label for=\"ID-select\">Data column for IDs: </label>\n        <select name=\"ID\" id=\"ID-select\">\n        ";
  foundHelper = helpers.allColumns;
  stack1 = foundHelper || depth0.allColumns;
  stack2 = helpers.each;
  tmp1 = self.program(5, program5, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  stack1 = stack2.call(depth0, stack1, tmp1);
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n        </select>\n    </div>\n\n    ";
  buffer += "\n    <div id=\"first-line-header\" style=\"display: none;\">\n        <p>Possible headers: ";
  foundHelper = helpers.possibleHeaders;
  stack1 = foundHelper || depth0.possibleHeaders;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "possibleHeaders", { hash: {} }); }
  buffer += escapeExpression(stack1) + "\n        </p>\n        <label for=\"first-line-header-checkbox\">Use the above as column headers?</label>\n        <input type=\"checkbox\" name=\"include-id\" id=\"first-line-header-checkbox\"\n            ";
  foundHelper = helpers.usePossibleHeaders;
  stack1 = foundHelper || depth0.usePossibleHeaders;
  stack2 = helpers['if'];
  tmp1 = self.program(7, program7, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  stack1 = stack2.call(depth0, stack1, tmp1);
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "/>\n        <p class=\"help-text-small\">\n            It looks like Galaxy couldn't get proper column headers for this data.\n            Would you like to use the column headers above as column names to select columns?\n        </p>\n    </div>\n\n    <input id=\"render-button\" type=\"button\" value=\"Draw\" />\n    <div class=\"clear\"></div>";
  return buffer;});
})();