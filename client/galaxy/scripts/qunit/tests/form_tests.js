/**
 * mvc/tool/tool-form is unused.
 */

/* global QUnit */
import $ from "jquery";
import testApp from "qunit/test-app";
import InputElement from "mvc/form/form-input";
import Ui from "mvc/ui/ui-misc";
import FormData from "mvc/form/form-data";
import ToolForm from "mvc/tool/tool-form";
import Utils from "utils/utils";
import { getAppRoot } from "onload/loadConfig";

QUnit.module("Form test", {
    beforeEach: function() {
        testApp.create();
        $.fx.off = true;
    },
    afterEach: function() {
        testApp.destroy();
        $.fx.off = false;
    }
});

QUnit.test("tool-form", function(assert) {
    var toolform = new ToolForm.View({ id: "test" });
    $("body").prepend(toolform.$el);
    window.fakeserver.respond();

    var form = toolform.form;
    var output = "";
    for (var property in assert) {
        output += property + ": ; ";
    }
    assert.ok(
        form.$(".portlet-title-text").html() == "<b>_name</b> _description (Galaxy Version _version)",
        "Title correct"
    );
    var tour_ids = [];
    $("[tour_id]").each(function() {
        tour_ids.push($(this).attr("tour_id"));
    });
    assert.ok(
        JSON.stringify(tour_ids) == '["a","b|c","b|i","b|j","k_0|l","k_0|m|n","k_0|m|s","k_0|m|t"]',
        "Tour ids correct"
    );
    assert.ok(
        JSON.stringify(form.data.create()) ==
            '{"a":"","b|c":"h","b|i":"i","b|j":"j","k_0|l":"l","k_0|m|n":"r","k_0|m|s":"s","k_0|m|t":"t"}',
        "Created data correct"
    );
    var mapped_ids = [];
    form.data.matchModel(form.model.attributes, function(input, id) {
        mapped_ids.push($("#" + id).attr("tour_id"));
    });
    assert.ok(
        JSON.stringify(mapped_ids) == '["a","b|c","b|i","b|j","k_0|l","k_0|m|n","k_0|m|s","k_0|m|t"]',
        "Remapped tour ids correct"
    );
    var dropdown = form.$("#menu > .dropdown-menu");
    assert.ok(dropdown.children().length == 2, "Found two menu items");
    dropdown
        .find(".fa-info-circle")
        .parent()
        .click();
    assert.ok(
        form.$(".alert").html() ===
            '<span>This tool requires req_name_a (Version req_version_a) and req_name_b (Version req_version_b). Click <a target="_blank" href="https://galaxyproject.org/tools/requirements/">here</a> for more information.</span>',
        "Check requirements message"
    );
    assert.ok(form.$(".form-repeat-delete").css("display") == "none", "Delete button disabled");
    var $add = form.$(".form-repeat-add");
    assert.ok(!$add.attr("disabled"), "Adding new repeat possible");
    $add.click();
    assert.ok($add.attr("disabled"), "Adding new repeat has been disabled");
    form.$(".form-repeat-delete").each(function(i, d) {
        assert.ok($(d).css("display") == "block", "Delete buttons " + i + " enabled");
    });
    assert.ok(
        JSON.stringify(form.data.create()) ==
            '{"a":"","b|c":"h","b|i":"i","b|j":"j","k_0|l":"l","k_0|m|n":"r","k_0|m|s":"s","k_0|m|t":"t","k_1|l":"l","k_1|m|n":"o","k_1|m|p":"p","k_1|m|q":"q"}',
        "Created data correct, after adding repeat"
    );
    form.$(".form-repeat-delete:first").click();
    assert.ok(form.$(".form-repeat-delete").css("display") == "none", "Delete button disabled");
    assert.ok(
        JSON.stringify(form.data.create()) ==
            '{"a":"","b|c":"h","b|i":"i","b|j":"j","k_0|l":"l","k_0|m|n":"o","k_0|m|p":"p","k_0|m|q":"q"}',
        "Created data correct, after removing first repeat"
    );
});

QUnit.test("data", function(assert) {
    var visits = [];
    Utils.get({
        url: getAppRoot() + "api/tools/test/build",
        success: function(response) {
            FormData.visitInputs(response.inputs, function(node, name, context) {
                visits.push({ name: name, node: node });
            });
        }
    });
    window.fakeserver.respond();
    assert.ok(
        JSON.stringify(visits) ==
            '[{"name":"a","node":{"name":"a","type":"text"}},{"name":"b|c","node":{"name":"c","type":"select","value":"h","options":[["d","d",false],["h","h",false]]}},{"name":"b|i","node":{"name":"i","type":"text","value":"i"}},{"name":"b|j","node":{"name":"j","type":"text","value":"j"}},{"name":"k_0|l","node":{"name":"l","type":"text","value":"l"}},{"name":"k_0|m|n","node":{"name":"n","type":"select","value":"r","options":[["o","o",false],["r","r",false]]}},{"name":"k_0|m|s","node":{"name":"s","type":"text","value":"s"}},{"name":"k_0|m|t","node":{"name":"t","type":"text","value":"t"}}]',
        "Testing value visitor"
    );
});

QUnit.test("input", function(assert) {
    var input = new InputElement(
        {},
        {
            field: new Ui.Input({})
        }
    );
    $("body").prepend(input.$el);
    assert.ok(input.$field.css("display") == "block", "Input field shown");
    assert.ok(input.$preview.css("display") == "none", "Preview hidden");
    assert.ok(input.$collapsible.css("display") == "none", "Collapsible hidden");
    assert.ok(input.$title_text.css("display") == "inline", "Title visible");
    assert.ok(input.$title_text.html() == "", "Title content unavailable");
    input.model.set("label", "_label");
    assert.ok(input.$title_text.html() == "_label", "Title content available");
    assert.ok(input.$error.css("display") == "none", "Error hidden");
    input.model.set("error_text", "_error_text");
    assert.ok(input.$error.css("display") == "block", "Error visible");
    assert.ok(input.$error_text.html() == "_error_text", "Error text correct");
    input.model.set("error_text", null);
    assert.ok(input.$error.css("display") == "none", "Error hidden, again");
    assert.ok(input.$backdrop.css("display") == "none", "Backdrop hidden");
    input.model.set("backdrop", true);
    assert.ok(input.$backdrop.css("display") == "block", "Backdrop shown");
    assert.ok(input.$backdrop.css("opacity") == 0, "Backdrop transparent");
    assert.ok(input.$backdrop.css("cursor") == "default", "Backdrop regular cursor");
    input.model.set("backdrop", false);
    assert.ok(input.$backdrop.css("display") == "none", "Backdrop hidden, again");
    input.model.set("disabled", true);
    assert.ok(input.$field.css("display") == "none", "Input field hidden");
    input.model.set("disabled", false);
    assert.ok(input.$field.css("display") == "block", "Input field shown, again");
    var colorElement = input.$field.children().first();
    var oldColor = colorElement.css("color");
    input.model.set("color", "red");
    assert.ok(colorElement.css("color") == "rgb(255, 0, 0)", "Shows correct new color");
    input.model.set("color", null);
    assert.ok(colorElement.css("color") == oldColor, "Shows correct old color");
    input.model.set("collapsible_value", "_collapsible_value");
    assert.ok(input.$collapsible.css("display") == "block", "Collapsible field");
    assert.ok(input.$collapsible_text.html() == "_label", "Title content available");
    assert.ok(input.$title_text.css("display") == "none", "Regular title not visible");
    input.model.set("help", "_help");
    assert.ok(input.$info.html() == "_help", "Correct help text");
    input.model.set("argument", "_argument");
    assert.ok(input.$info.html() == "_help (_argument)", "Correct help text with argument");
    input.model.set("help", "_help (_argument)");
    assert.ok(input.$info.html() == "_help (_argument)", "Correct help text with argument from help");
});
