/* global QUnit */
import $ from "jquery";
import testApp from "qunit/test-app";
import GalaxyModal from "mvc/ui/ui-modal";

QUnit.module("Modal dialog test", {
    beforeEach: function() {
        $.fx.off = true;
        testApp.create();
        var self = this;
        this.app = new GalaxyModal.View({
            title: "Test title",
            body: "Test body",
            buttons: {
                Ok: function() {},
                Cancel: function() {
                    self.app.hide();
                }
            }
        });
    },
    afterEach: function() {
        $.fx.off = false;
        testApp.destroy();
        this.app.$el.remove();
    }
});

QUnit.test("test dialog attributes", function(assert) {
    assert.ok(this.app.$header.find(".title").html() == "Test title", "Modal header has correct title.");
    assert.ok(this.app.$body.html() == "Test body", "Modal header has correct body.");
});

QUnit.test("test dialog visibility", function(assert) {
    this.app.hide();
    assert.ok(this.app.$el.css("display") == "none", "Modal hidden manually");
    this.app.show();
    assert.ok(this.app.$el.css("display") == "block", "Modal shown manually");
    this.app.getButton("Ok").trigger("click");
    assert.ok(this.app.$el.css("display") == "block", "Modal still visible after clicking Ok");
    this.app.getButton("Cancel").trigger("click");
    assert.ok(this.app.$el.css("display") == "none", "Modal hidden after clicking Cancel");
    this.app.show();
    assert.ok(this.app.$el.css("display") == "block", "Modal manually shown again");
    assert.ok(!this.app.$header.hasClass("no-separator"), "Title separator tagged as visible.");
    this.app.show({ title_separator: false });
    assert.ok(this.app.$header.hasClass("no-separator"), "Title separator tagged as hidden.");
    assert.ok(this.app.$backdrop.hasClass("in"), "Backdrop tagged as shown.");
    this.app.show({ backdrop: false });
    assert.ok(!this.app.$backdrop.hasClass("in"), "Backdrop tagged as hidden.");
});

QUnit.test("test dialog closing events", function(assert) {
    this.app.show();
    this.app.$backdrop.trigger("click");
    assert.ok(this.app.$el.css("display") == "block", "Modal shown after backdrop click");
    this.app.hide();
    this.app.show({ closing_events: true });
    assert.ok(this.app.$el.css("display") == "block", "Modal shown with closing events");
    this.app.$backdrop.trigger("click");
    assert.ok(this.app.$el.css("display") == "none", "Modal hidden after backdrop click");
});

QUnit.test("test dialog rendering", function(assert) {
    var before = this.app.$el.html();
    this.app.render();
    assert.ok(before == this.app.$el.html(), "Re-rendering successful");
    this.app.options.title = "New Title";
    this.app.render();
    assert.ok(this.app.$header.find(".title").html() == "New Title", "Modal header has correct new title.");
});

QUnit.test("test button states", function(assert) {
    assert.ok(this.app.getButton("Ok").html() === "Ok", "Ok has correct label");
    assert.ok(!this.app.getButton("Ok").prop("disabled"), "Ok is active");
    assert.ok(!this.app.getButton("Cancel").prop("disabled"), "Cancel is active");
    this.app.disableButton("Ok");
    assert.ok(this.app.getButton("Ok").prop("disabled"), "Ok is disabled");
    assert.ok(!this.app.getButton("Cancel").prop("disabled"), "Cancel is still active");
    this.app.disableButton("Cancel");
    assert.ok(this.app.getButton("Cancel").prop("disabled"), "Cancel is also disabled");
    assert.ok(this.app.getButton("Ok").prop("disabled"), "Ok is still disabled");
    this.app.enableButton("Ok");
    assert.ok(this.app.getButton("Cancel").prop("disabled"), "Cancel is still disabled");
    assert.ok(!this.app.getButton("Ok").prop("disabled"), "Ok is active again");
});
