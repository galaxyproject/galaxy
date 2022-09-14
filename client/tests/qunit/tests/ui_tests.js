/* global QUnit */
import $ from "jquery";
import testApp from "../test-app";
import sinon from "sinon";
import Ui from "mvc/ui/ui-misc";
import SelectContent from "mvc/ui/ui-select-content";
import Drilldown from "mvc/ui/ui-drilldown";
import Tabs from "mvc/ui/ui-tabs";

QUnit.module("Ui test", {
    beforeEach: function () {
        testApp.create();
        this.clock = sinon.useFakeTimers();
    },
    afterEach: function () {
        testApp.destroy();
        this.clock.restore();
    },
});

QUnit.test("tabs", function (assert) {
    assert.ok($.fn);
    var self = this;
    var tabs = new Tabs.View({});
    var collection = tabs.collection;
    collection.add({ id: "id_a", title: "title_a", icon: "icon_a", $el: "el_a" });
    var _test = function () {
        self.clock.tick(window.WAIT_FADE);
        collection.each(function (model, index) {
            var $tab_element = tabs.$("#tab-" + model.id + " .nav-link");
            var $tab_content = tabs.$("#" + model.id);
            var is_current = model.id == tabs.model.get("current");
            assert.ok($tab_content.hasClass("active") == is_current, "Active state of content.");
            assert.ok($tab_element.hasClass("active") == is_current, "Active state of element.");
        });
    };
    $("body").prepend(tabs.$el);
    _test();
    collection.add({ id: "id_b", title: "title_b", icon: "icon_b", $el: "el_b" });
    _test();
    tabs.collection.get("id_b").set("hidden", true);
    _test();
    collection.add({ id: "id_c", title: "title_c", icon: "icon_c", $el: "el_c" });
    tabs.model.set("current", "id_c");
    _test();
    tabs.collection.get("id_b").set("hidden", false);
    _test();
    tabs.model.set("current", "id_b");
    _test();
    tabs.model.set("visible", false);
    tabs.collection.reset();
    self.clock.tick(window.WAIT_FADE);
    assert.ok(tabs.$el.css("display", "none"), "Everything hidden.");
    tabs.model.set("visible", true);
    self.clock.tick(window.WAIT_FADE);
    assert.ok(tabs.$el.css("display", "block"), "Everything shown.");
    collection.add({ id: "id_c", title: "title_c", icon: "icon_c", $el: "el_c" });
    tabs.model.set("current", "id_c");
    _test();
});

QUnit.test("button-default", function (assert) {
    var button = new Ui.Button({ title: "title" });
    var model = button.model;
    $("body").prepend(button.$el);
    assert.ok(button.$title.html() == "title", "Has correct title");
    model.set("title", "_title");
    assert.ok(button.$title.html() == "_title", "Has correct new title");
    assert.ok(!button.$el.attr("disabled"), "Button active");
    model.set("disabled", true);
    assert.ok(button.$el.attr("disabled"), "Button disabled");
    model.set("disabled", false);
    assert.ok(!button.$el.attr("disabled"), "Button active, again");
    model.set("wait", true);
    assert.ok(button.$title.html() == model.get("wait_text"), "Shows correct wait text");
    model.set("wait_text", "wait_text");
    assert.ok(button.$title.html() == "wait_text", "Shows correct new wait text");
    model.set("wait", false);
    assert.ok(button.$title.html() == model.get("title"), "Shows correct regular title");
});

QUnit.test("button-default", function (assert) {
    var button = new Ui.Button({ title: "title" });
    var model = button.model;
    $("body").prepend(button.$el);
    assert.ok(button.$title.html() == "title", "Has correct title");
    model.set("title", "_title");
    assert.ok(button.$title.html() == "_title", "Has correct new title");
    assert.ok(!button.$el.attr("disabled"), "Button active");
    model.set("disabled", true);
    assert.ok(button.$el.attr("disabled"), "Button disabled");
    model.set("disabled", false);
    assert.ok(!button.$el.attr("disabled"), "Button active, again");
    model.set("wait", true);
    assert.ok(button.$title.html() == model.get("wait_text"), "Shows correct wait text");
    model.set("wait_text", "wait_text");
    assert.ok(button.$title.html() == "wait_text", "Shows correct new wait text");
    model.set("wait", false);
    assert.ok(button.$title.html() == model.get("title"), "Shows correct regular title");
});

QUnit.test("button-check", function (assert) {
    var button = new Ui.ButtonCheck({ title: "title" });
    var model = button.model;
    $("body").prepend(button.$el);
    assert.ok(button.$title.html() == "title", "Has correct title");
    model.set("title", "_title");
    assert.ok(button.$title.html() == "_title", "Has correct new title");
    assert.ok(button.$icon.hasClass(button.model.get("icons")[0]), "Has correct " + model.get("value") + " value");
    button.value(1);
    assert.ok(button.$icon.hasClass(button.model.get("icons")[1]), "Has correct " + model.get("value") + " value");
    button.value(2);
    assert.ok(button.$icon.hasClass(button.model.get("icons")[2]), "Has correct " + model.get("value") + " value");
    button.value(0, 100);
    assert.ok(
        button.$icon.hasClass(button.model.get("icons")[0]),
        "Has correct " + model.get("value") + " value after fraction"
    );
    button.value(10, 100);
    assert.ok(
        button.$icon.hasClass(button.model.get("icons")[1]),
        "Has correct " + model.get("value") + " value after fraction"
    );
    button.value(100, 100);
    assert.ok(
        button.$icon.hasClass(button.model.get("icons")[2]),
        "Has correct " + model.get("value") + " value after fraction"
    );
    button.$el.trigger("click");
    assert.ok(
        button.$icon.hasClass(button.model.get("icons")[0]),
        "Has correct " + model.get("value") + " value after click"
    );
    button.$el.trigger("click");
    assert.ok(
        button.$icon.hasClass(button.model.get("icons")[2]),
        "Has correct " + model.get("value") + " value after click"
    );
    button.$el.trigger("click");
    assert.ok(
        button.$icon.hasClass(button.model.get("icons")[0]),
        "Has correct " + model.get("value") + " value after click"
    );
});

QUnit.test("options", function (assert) {
    function _test(obj, options) {
        assert.ok(JSON.stringify(obj.value()) == JSON.stringify(options.value), "Selected value is " + options.value);
        assert.ok(
            obj.$menu.css("display") == (options.menu_visible ? "block" : "none"),
            "Menu visibility: " + options.menu_visible
        );
        assert.ok(
            obj.$message.css("display") == (options.message_visible ? "block" : "none"),
            "Message visibility: " + options.message_visible
        );
        assert.ok(
            obj.$options.css("display") == (options.options_visible ? "inline-block" : "none"),
            "Options visibility: " + options.options_visible
        );
        options.message_cls &&
            assert.ok(obj.$message.hasClass(options.message_cls), "Message has class: " + options.message_cls);
        assert.ok(obj.length() === options.length, "Number of options: " + options.length);
        options.message_text &&
            assert.ok(obj.$message.html() === options.message_text, "Message text is: " + options.message_text);
        options.first && assert.ok(obj.first() === options.first, "First value is: " + options.first);
        options.all_icon &&
            assert.ok(
                obj.all_button.$(".icon").hasClass(options.all_icon),
                "All button in correct state: " + options.all_icon
            );
        assert.ok(
            obj.$menu.find(".ui-button-check").length === (options.all_icon ? 1 : 0),
            "All button available: " + Boolean(options.all_active)
        );
    }

    var radio = new Ui.Radio.View({});
    $("body").prepend(radio.$el);
    radio.model.set("visible", false);
    assert.ok(radio.value() === null, "Initial value is `null`.");
    assert.ok(radio.$el.css("display") === "none", "Options hidden.");
    radio.model.set("visible", true);
    assert.ok(radio.$el.css("display") === "block", "Options shown.");
    radio.model.set("value", "Unavailable.");
    assert.ok(radio.value() === null, "Unavailable value ignored.");
    _test(radio, {
        menu_visible: false,
        message_visible: true,
        message_text: "No options available.",
        message_cls: "alert-danger",
        options_visible: false,
        value: null,
        length: 0,
    });
    radio.model.set("wait", true);
    _test(radio, {
        menu_visible: false,
        message_visible: true,
        message_text: "Please wait...",
        message_cls: "alert-info",
        options_visible: false,
        value: null,
        length: 0,
    });
    radio.model.set("wait", false);
    _test(radio, {
        menu_visible: false,
        message_visible: true,
        message_text: "No options available.",
        message_cls: "alert-danger",
        options_visible: false,
        value: null,
        length: 0,
    });
    radio.model.set("data", [
        { value: "valuea", label: "labela" },
        { value: "valueb", label: "labelb" },
    ]);
    _test(radio, {
        menu_visible: true,
        message_visible: false,
        options_visible: true,
        value: "valuea",
        first: "valuea",
        length: 2,
    });
    radio.model.set("value", "valueb");
    _test(radio, {
        menu_visible: true,
        message_visible: false,
        options_visible: true,
        value: "valueb",
        first: "valuea",
        length: 2,
    });
    radio.model.set("data", null);
    _test(radio, {
        menu_visible: false,
        message_visible: true,
        message_text: "No options available.",
        message_cls: "alert-danger",
        options_visible: false,
        value: null,
        first: null,
        length: 0,
    });
    radio.model.set("data", [
        { value: "valuea", label: "labela" },
        { value: "valueb", label: "labelb" },
        { value: "valuec", label: "labelc" },
    ]);
    _test(radio, {
        menu_visible: true,
        message_visible: false,
        options_visible: true,
        value: "valueb",
        first: "valuea",
        length: 3,
    });
    radio.$("input").last().click();
    _test(radio, {
        menu_visible: true,
        message_visible: false,
        options_visible: true,
        value: "valuec",
        first: "valuea",
        length: 3,
    });

    var check = new Ui.Checkbox.View({});
    $("body").prepend(check.$el);
    _test(check, {
        menu_visible: false,
        message_visible: true,
        message_text: "No options available.",
        message_cls: "alert-danger",
        options_visible: false,
        value: null,
        length: 0,
        all_icon: "fa-square-o",
    });
    check.model.set("data", [
        { value: "valuea", label: "labela" },
        { value: "valueb", label: "labelb" },
        { value: "valuec", label: "labelc" },
    ]);
    _test(check, {
        menu_visible: true,
        message_visible: false,
        options_visible: true,
        value: null,
        length: 3,
        all_icon: "fa-square-o",
    });
    check.model.set("value", ["valuea", "valuec"]);
    _test(check, {
        menu_visible: true,
        message_visible: false,
        options_visible: true,
        value: ["valuea", "valuec"],
        length: 3,
        all_icon: "fa-minus-square-o",
    });
    check.model.set("value", ["valuea", "valueb", "valuec"]);
    _test(check, {
        menu_visible: true,
        message_visible: false,
        options_visible: true,
        value: ["valuea", "valueb", "valuec"],
        length: 3,
        all_icon: "fa-check-square-o",
    });
    check.model.set("data", []);
    _test(check, {
        menu_visible: false,
        message_visible: true,
        options_visible: false,
        value: null,
        length: 0,
        all_icon: "fa-square-o",
    });
    check.model.set("data", [
        { value: "valuea", label: "labela" },
        { value: "valueb", label: "labelb" },
    ]);
    _test(check, {
        menu_visible: true,
        message_visible: false,
        options_visible: true,
        value: ["valuea", "valueb"],
        first: "valuea",
        length: 2,
        all_icon: "fa-check-square-o",
    });
    check.all_button.$el.click();
    _test(check, {
        menu_visible: true,
        message_visible: false,
        options_visible: true,
        value: null,
        first: "valuea",
        length: 2,
        all_icon: "fa-square-o",
    });
    check.all_button.$el.click();
    _test(check, {
        menu_visible: true,
        message_visible: false,
        options_visible: true,
        value: ["valuea", "valueb"],
        first: "valuea",
        length: 2,
        all_icon: "fa-check-square-o",
    });
    check.$("input").last().click();
    _test(check, {
        menu_visible: true,
        message_visible: false,
        options_visible: true,
        value: ["valuea"],
        first: "valuea",
        length: 2,
        all_icon: "fa-minus-square-o",
    });
    check.$("input").last().click();
    _test(check, {
        menu_visible: true,
        message_visible: false,
        options_visible: true,
        value: ["valuea", "valueb"],
        first: "valuea",
        length: 2,
        all_icon: "fa-check-square-o",
    });

    var radiobutton = new Ui.RadioButton.View({});
    $("body").prepend(radiobutton.$el);
    radiobutton.model.set("data", [
        { value: "valuea", label: "labela" },
        { value: "valueb", label: "labelb" },
    ]);
    _test(radiobutton, {
        menu_visible: true,
        message_visible: false,
        options_visible: true,
        value: "valuea",
        first: "valuea",
        length: 2,
    });
    radiobutton.$("input").last().click();
    _test(radiobutton, {
        menu_visible: true,
        message_visible: false,
        options_visible: true,
        value: "valueb",
        first: "valuea",
        length: 2,
    });

    var drilldown = new Drilldown.View({});
    $("body").prepend(drilldown.$el);
    drilldown.model.set("data", [
        {
            value: "valuea",
            name: "labela",
            options: [
                { value: "valueb", name: "labelb" },
                { value: "valuec", name: "labelc" },
                {
                    value: "valued",
                    name: "labeld",
                    options: [
                        { value: "valuee", name: "labele" },
                        { value: "valuef", name: "labelf" },
                    ],
                },
            ],
        },
        {
            value: "valueg",
            name: "labelg",
            options: [
                { value: "valueh", name: "labelh" },
                { value: "valuei", name: "labeli" },
                {
                    value: "valuej",
                    name: "labelj",
                    options: [
                        { value: "valuek", name: "labelk" },
                        { value: "valuel", name: "labell" },
                        { value: "valuem", name: "labelm" },
                    ],
                },
            ],
        },
        { value: "valuen", name: "labeln" },
    ]);
    _test(drilldown, {
        menu_visible: true,
        message_visible: false,
        options_visible: true,
        value: null,
        first: "valuea",
        length: 14,
        all_icon: "fa-square-o",
    });
    drilldown.model.set("value", ["valuek", "valuen"]);
    _test(drilldown, {
        menu_visible: true,
        message_visible: false,
        options_visible: true,
        value: ["valuek", "valuen"],
        first: "valuea",
        length: 14,
        all_icon: "fa-minus-square-o",
    });
    var drillradio = new Drilldown.View({ display: "radio" });
    $("body").prepend(drillradio.$el);
    _test(drillradio, {
        menu_visible: false,
        message_visible: true,
        options_visible: false,
        value: null,
        length: 0,
    });
    drillradio.model.set("data", drilldown.model.get("data"));
    _test(drillradio, {
        menu_visible: true,
        message_visible: false,
        options_visible: true,
        value: "valuea",
        first: "valuea",
        length: 14,
    });
});

QUnit.test("select-default", function (assert) {
    function _test(options) {
        assert.ok(
            JSON.stringify(select.value()) == JSON.stringify(options.value),
            "Selected value is " + options.value
        );
        assert.ok(select.text() == options.label, "Selected label is " + options.label);
        assert.ok(select.$el.display === options.visible ? "block" : "none", options.visible ? "Visible" : "Hidden");
        assert.ok(select.data.length === options.count && select.length(), "Found " + options.count + " option");
        options.exists && assert.ok(select.exists(options.exists), "Found value: " + options.exists);
        assert.ok(
            select.$select.prop("multiple") === Boolean(options.multiple),
            "Multiple state set to: " + options.multiple
        );
        assert.ok(Boolean(select.all_button) === Boolean(options.multiple), "Visiblity of select all button correct.");
        options.multiple &&
            assert.ok(
                select.all_button.$(".icon").hasClass(options.all_icon),
                "All button in correct state: " + options.all_icon
            );
    }
    var select = new Ui.Select.View({});
    $("body").prepend(select.$el);
    assert.ok(select.first() === "__null__", "First select is '__null__'");
    assert.ok(select.$dropdown.hasClass("fa-caret-down"), "Caret down shown.");
    select.model.set("data", [{ value: "value", label: "label" }]);
    _test({
        value: "value",
        label: "label",
        visible: true,
        count: 1,
    });
    select.model.set("data", [
        { value: "valuea", label: "labela" },
        { value: "valueb", label: "labelb" },
    ]);
    _test({
        value: "valuea",
        label: "labela",
        visible: true,
        count: 2,
        exists: "valueb",
    });
    select.value("valueb");
    _test({
        value: "valueb",
        label: "labelb",
        visible: true,
        count: 2,
    });
    select.model.set("data", [{ value: "value", label: "label" }]);
    _test({
        value: "value",
        label: "label",
        visible: true,
        count: 1,
    });
    select.model.set({ visible: false, value: "unavailable" });
    _test({
        value: "value",
        label: "label",
        visible: false,
        count: 1,
    });
    select.model.set({
        visible: true,
        value: "valueb",
        data: [
            { value: "valuea", label: "labela" },
            { value: "valueb", label: "labelb" },
        ],
    });
    _test({
        value: "valueb",
        label: "labelb",
        visible: true,
        count: 2,
        exists: "valuea",
    });
    select.model.set({ multiple: true });
    _test({
        value: ["valueb"],
        label: "labelb",
        visible: true,
        count: 2,
        exists: "valuea",
        multiple: true,
        all_icon: "fa-minus-square-o",
    });
    select.model.set("value", ["valueb", "valuea"]);
    _test({
        value: ["valuea", "valueb"],
        label: "labela",
        visible: true,
        count: 2,
        exists: "valueb",
        multiple: true,
        all_icon: "fa-check-square-o",
    });
    select.model.set("value", []);
    _test({
        value: null,
        label: "",
        visible: true,
        count: 2,
        exists: "valuea",
        multiple: true,
        all_icon: "fa-square-o",
    });
    select.model.set({ multiple: false });
    _test({
        value: "valuea",
        label: "labela",
        visible: true,
        count: 2,
        exists: "valuea",
    });
    select.model.set({ visible: false });
    _test({
        value: "valuea",
        label: "labela",
        visible: false,
        count: 2,
        exists: "valuea",
    });
    select.model.set({
        multiple: true,
        visible: true,
        value: ["valueb", "valuec"],
        data: [
            { value: "valuea", label: "labela" },
            { value: "valueb", label: "labelb" },
            { value: "valuec", label: "labelc" },
        ],
    });
    _test({
        value: ["valueb", "valuec"],
        label: "labelb",
        visible: true,
        count: 3,
        exists: "valuea",
        multiple: true,
        all_icon: "fa-minus-square-o",
    });
});

QUnit.test("input", function (assert) {
    var input = new Ui.Input();
    $("body").prepend(input.$el);
    assert.ok(input.tagName === "input", "Created input.");
    assert.ok(input.value() === undefined, "Input empty.");
    input.model.set("value", "_value");
    assert.ok(input.$el.val() === "_value", "Input with value.");
    assert.ok(!input.$el.hasClass("_cls"), "Has no custom class.");
    input.model.set("cls", "_cls");
    assert.ok(input.$el.hasClass("_cls"), "Has custom class.");
    assert.ok(!input.$el.attr("placeholder"), "Has no placeholder");
    input.model.set("placeholder", "_placeholder");
    assert.ok(input.$el.attr("placeholder") === "_placeholder", "Has correct placeholder");
    input.model.set("disabled", true);
    assert.ok(input.$el.attr("disabled"), "Disabled");
    input.model.set("disabled", false);
    assert.ok(!input.$el.attr("disabled"), "Enabled");
    input.model.set("visible", false);
    assert.ok(input.$el.css("display") === "none", "Hidden");
    input.model.set("visible", true);
    assert.ok(input.$el.css("display") === "inline-block", "Shown");
});

QUnit.test("textarea", function (assert) {
    var input = new Ui.Input({ area: true });
    $("body").prepend(input.$el);
    assert.ok(input.tagName === "textarea", "Created textarea.");
    assert.ok(input.value() === undefined, "Unavailable value.");
    input.model.set("value", "_value");
    assert.ok(input.value() === "_value", "Correct new value.");
    assert.ok(!input.$el.hasClass("_cls"), "Has no custom class.");
    input.model.set("cls", "_cls");
    assert.ok(input.$el.hasClass("_cls"), "Has custom class.");
});

QUnit.test("nullableText", function (assert) {
    // Start with null value, optional button should be off
    var input = new Ui.NullableText({ area: false, value: null });
    $("body").prepend(input.$el);
    assert.ok(input.text_input.tagName === "input", "input tag");
    assert.ok(input.value() === null, "null value");
    assert.ok(input.optional_button.model.get("value") === "false");
    // toggle button, will set value to `""`
    input.optional_button.model.set("value", "true");
    assert.ok(input.value() === "", "Correct new value.");
    // set value
    input.text_input.model.set("value", "_value");
    assert.ok(input.value() === "_value", "Correct new value.");
    assert.ok(input.optional_button.model.get("value") === "true");
    // toggle button to false, will reset value to null
    input.optional_button.model.set("value", "false");
    assert.ok(input.value() === null, "Correct new value.");
    assert.ok(input.optional_button.model.get("value") === "false");
    // New input, start with value, optional button should be on
    var definedInput = new Ui.NullableText({ area: false, value: "123" });
    assert.ok(definedInput.value() === "123");
    assert.ok(definedInput.optional_button.model.get("value") === "true");
});

QUnit.test("message", function (assert) {
    var message = new Ui.Message({
        persistent: true,
        message: "_message",
        status: "danger",
    });
    $("body").prepend(message.$el);
    assert.ok(message.$el.hasClass("alert-danger"), "Alert danger.");
    message.model.set("status", "info");
    assert.ok(!message.$el.hasClass("alert-danger"), "Alert danger (disabled).");
    assert.ok(message.$el.hasClass("alert-info"), "Alert info.");
    assert.ok(message.$el.html() === "_message", "Correct message.");
    message.model.set("message", "_new_message");
    assert.ok(message.$el.html() === "_new_message", "Correct new message.");
});

QUnit.test("select-content", function (assert) {
    var select = new SelectContent.View({});
    $("body").prepend(select.$el);
    var _testSelect = function (tag, options) {
        var field = select.fields[tag == "first" ? 0 : select.fields.length - 1];
        var $select = select.$(".ui-select:" + tag);
        var $button = select.$(".ui-radiobutton").find("label:" + tag);
        assert.ok(field.length() == options[tag + "length"], tag + " one has " + options[tag + "length"] + " options");
        assert.ok(field.data[0].value == options[tag + "value"], tag + " option has correct value");
        assert.ok(field.data[0].label == options[tag + "label"], tag + " option has correct label");
        assert.ok($select.hasClass("ui-select-multiple") == options[tag + "multiple"], "Check multiple option");
        $button.trigger("mouseover");
        var tooltip = $(".tooltip-inner:last").text();
        $button.trigger("mouseleave");
        assert.ok(tooltip.indexOf("dataset") != -1 || tooltip.indexOf("collection") != -1, "Basic tooltip check");
    };
    var _test = function (options) {
        assert.ok(select.button_type.$(".ui-option:first").hasClass("active"), "First one is toggled");
        assert.ok(
            select.$(".ui-select").length == options.selectfields,
            "Found " + options.selectfields + " select fields"
        );
        assert.ok(
            select.button_type.$(".ui-option").length == options.selectfields,
            "Found " + options.selectfields + " radio button options"
        );
        assert.ok(
            select.$(".ui-select-multiple").length == options.totalmultiple,
            "Contains " + options.totalmultiple + " multiselect fields"
        );
        assert.ok(
            select.$el.find(".ui-options:first .ui-option").length === options.selectfields,
            "Radio button count, expected " + options.selectfields
        );
        assert.ok(select.$(".ui-select:first").css("display") == "block", "Check select visibility");
        assert.ok(
            select.$(".ui-select:last").css("display") == (options.selectfields == 1 ? "block" : "none"),
            "Last select visibility"
        );
        assert.ok(
            (select.button_dialog.$el.css("display") != "none") === options.showdialog,
            "Data dialog button visible"
        );
        _testSelect("first", options);
        _testSelect("last", options);
    };

    assert.ok(select.button_type.value() == 0, "Initial mode selected by default.");
    select.model.set("data", {
        hda: [
            { id: "id0", name: "name0", hid: "hid0" },
            { id: "id1", name: "name1", hid: "hid1" },
        ],
        hdca: [
            { id: "id2", name: "name2", hid: "hid2" },
            { id: "id3", name: "name3", hid: "hid3" },
            { id: "id4", name: "name4", hid: "hid4" },
        ],
    });

    var initial = {
        selectfields: 3,
        firstlength: 2,
        firstvalue: "id0",
        firstlabel: "hid0: name0",
        firstmultiple: false,
        totalmultiple: 1,
        lastvalue: "id2",
        lastlabel: "hid2: name2",
        lastlength: 3,
        lastmultiple: false,
        showdialog: true,
    };
    _test(initial);

    select.model.set("multiple", true);
    select.model.set("type", "data");
    _test({
        selectfields: 2,
        firstlength: 2,
        firstvalue: "id0",
        firstlabel: "hid0: name0",
        firstmultiple: true,
        totalmultiple: 2,
        lastvalue: "id2",
        lastlabel: "hid2: name2",
        lastlength: 3,
        lastmultiple: true,
        showdialog: true,
    });

    select.model.set("multiple", false);
    select.model.set("type", "data_collection");
    _test({
        selectfields: 1,
        firstlength: 3,
        firstvalue: "id2",
        firstlabel: "hid2: name2",
        firstmultiple: false,
        totalmultiple: 0,
        lastvalue: "id2",
        lastlabel: "hid2: name2",
        lastlength: 3,
        lastmultiple: false,
        showdialog: false,
    });

    select.model.set("type", "module_data_collection");
    _test({
        selectfields: 2,
        firstlength: 3,
        firstvalue: "id2",
        firstlabel: "hid2: name2",
        firstmultiple: false,
        totalmultiple: 1,
        lastvalue: "id2",
        lastlabel: "hid2: name2",
        lastlength: 3,
        lastmultiple: true,
        showdialog: false,
    });

    select.model.set("type", "module_data");
    _test({
        selectfields: 2,
        firstlength: 2,
        firstvalue: "id0",
        firstlabel: "hid0: name0",
        firstmultiple: false,
        totalmultiple: 1,
        lastvalue: "id0",
        lastlabel: "hid0: name0",
        lastlength: 2,
        lastmultiple: true,
        showdialog: true,
    });

    select.model.set("type", "data");
    _test(initial);

    select.model.set("wait", true);
    assert.ok(select.$(".icon-dropdown").hasClass("fa-spinner"), "Shows spinner");
    select.model.set("wait", false);
    assert.ok(select.$(".icon-dropdown").hasClass("fa-caret-down"), "Shows caret");
    select.model.set("optional", true);
    assert.ok(select.fields[0].data[0].value == "__null__", "First option is optional value");
    select.model.set("optional", false);
    assert.ok(select.fields[0].data[0].value != "__null__", "First option is not optional value");

    select.model.set("value", { values: [{ id: "id1", src: "hda" }] });
    assert.ok(
        JSON.stringify(select.value()) == '{"values":[{"id":"id1","name":"name1","hid":"hid1"}],"batch":false}',
        "Checking single value"
    );

    assert.ok(select.config[select.model.get("current")].src == "hda", "Matched dataset field");
    assert.ok(!select.config[select.model.get("current")].multiple, "Matched single select field");
    select.model.set("value", {
        values: [
            { id: "id0", src: "hda" },
            { id: "id1", src: "hda" },
        ],
    });
    assert.ok(select.config[select.model.get("current")].multiple, "Matched multiple field");
    assert.ok(
        JSON.stringify(select.value()) ==
            '{"values":[{"id":"id0","name":"name0","hid":"hid0"},{"id":"id1","name":"name1","hid":"hid1"}],"batch":true}',
        "Checking multiple values"
    );
    select.model.set("value", { values: [{ id: "id2", src: "hdca" }] });
    assert.ok(select.config[select.model.get("current")].src == "hdca", "Matched collection field");
    assert.ok(
        JSON.stringify(select.value()) == '{"values":[{"id":"id2","name":"name2","hid":"hid2"}],"batch":true}',
        "Checking collection value"
    );

    select = new SelectContent.View({});
    $("body").prepend(select.$el);
    var _testEmptySelect = function (tag, txt_extension, txt_label) {
        var field = select.fields[tag == "first" ? 0 : select.fields.length - 1];
        select.$(".ui-select:" + tag);
        assert.ok(field.data[0].value == "__null__", tag + " option has correct empty value.");
        assert.ok(
            field.data[0].label == "No " + txt_extension + txt_label + " available.",
            tag + " option has correct empty label."
        );
    };

    var labels = select.model.get("src_labels");
    _testEmptySelect("first", "", labels.hda);
    _testEmptySelect("last", "", labels.hdca);
    select.model.set("extensions", ["txt", "bam"]);
    _testEmptySelect("first", "txt or bam ", labels.hda);
    _testEmptySelect("last", "txt or bam ", labels.hdca);
    select.model.set("extensions", ["txt"]);
    _testEmptySelect("first", "txt ", labels.hda);
    _testEmptySelect("last", "txt ", labels.hdca);
});
