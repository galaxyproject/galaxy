this.Handlebars = this.Handlebars || {}, this.Handlebars.templates = this.Handlebars.templates || {}, 
this.Handlebars.templates.tool_form = Handlebars.template({
    "1": function(depth0, helpers, partials, data) {
        var stack1, helper, alias1 = helpers.helperMissing, alias2 = "function", alias3 = this.escapeExpression;
        return '        <div class="form-row">\n            <label for="' + alias3((helper = null != (helper = helpers.name || (null != depth0 ? depth0.name : depth0)) ? helper : alias1, 
        typeof helper === alias2 ? helper.call(depth0, {
            name: "name",
            hash: {},
            data: data
        }) : helper)) + '">' + alias3((helper = null != (helper = helpers.label || (null != depth0 ? depth0.label : depth0)) ? helper : alias1, 
        typeof helper === alias2 ? helper.call(depth0, {
            name: "label",
            hash: {},
            data: data
        }) : helper)) + ':</label>\n            <div class="form-row-input">\n                ' + (null != (helper = null != (helper = helpers.html || (null != depth0 ? depth0.html : depth0)) ? helper : alias1, 
        stack1 = typeof helper === alias2 ? helper.call(depth0, {
            name: "html",
            hash: {},
            data: data
        }) : helper) ? stack1 : "") + '\n            </div>\n            <div class="toolParamHelp" style="clear: both;">\n                ' + alias3((helper = null != (helper = helpers.help || (null != depth0 ? depth0.help : depth0)) ? helper : alias1, 
        typeof helper === alias2 ? helper.call(depth0, {
            name: "help",
            hash: {},
            data: data
        }) : helper)) + '\n            </div>\n            <div style="clear: both;"></div>\n        </div>\n';
    },
    compiler: [ 6, ">= 2.0.0-beta.1" ],
    main: function(depth0, helpers, partials, data) {
        var stack1, helper, alias1 = helpers.helperMissing, alias2 = "function", alias3 = this.escapeExpression;
        return '<div class="toolFormTitle">' + alias3((helper = null != (helper = helpers.name || (null != depth0 ? depth0.name : depth0)) ? helper : alias1, 
        typeof helper === alias2 ? helper.call(depth0, {
            name: "name",
            hash: {},
            data: data
        }) : helper)) + " (version " + alias3((helper = null != (helper = helpers.version || (null != depth0 ? depth0.version : depth0)) ? helper : alias1, 
        typeof helper === alias2 ? helper.call(depth0, {
            name: "version",
            hash: {},
            data: data
        }) : helper)) + ')</div>\n    <div class="toolFormBody">\n' + (null != (stack1 = helpers.each.call(depth0, null != depth0 ? depth0.inputs : depth0, {
            name: "each",
            hash: {},
            fn: this.program(1, data, 0),
            inverse: this.noop,
            data: data
        })) ? stack1 : "") + '    </div>\n    <div class="form-row form-actions">\n    <input type="submit" class="btn btn-primary" name="runtool_btn" value="Execute">\n</div>\n<div class="toolHelp">\n    <div class="toolHelpBody">' + alias3((helper = null != (helper = helpers.help || (null != depth0 ? depth0.help : depth0)) ? helper : alias1, 
        typeof helper === alias2 ? helper.call(depth0, {
            name: "help",
            hash: {},
            data: data
        }) : helper)) + "</div>\n</div>";
    },
    useData: !0
});