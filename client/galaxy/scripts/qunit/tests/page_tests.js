/* global QUnit */
import _ from "underscore";
import $ from "jquery";
import Backbone from "backbone";
import testApp from "qunit/test-app";
import Page from "layout/page";

QUnit.module("Page test", {
    beforeEach: function() {
        testApp.create();
        this.$container = $("<div/>").css("display", "none");
        $("body").append(this.$container);
    },
    afterEach: function() {
        testApp.destroy();
        this.$container.remove();
    }
});

function _check(assert, page, sidePanels) {
    assert.ok(page.$("#center").length == 1, "Center panel found.");
    _.each(sidePanels, function(panelVisible, panelId) {
        assert.ok(
            page.$("#" + panelId).css("display") == panelVisible,
            (panelVisible ? "" : "No") + " " + panelId + " panel found."
        );
    });
}

QUnit.test("test center/right", function(assert) {
    this.$container.empty();
    var page = new Page.View({
        Right: Backbone.View.extend({
            initialize: function() {
                this.setElement($("<div/>"));
                this.model = new Backbone.Model({});
            }
        })
    }).render();
    _check(assert, page, { left: "none", right: "block" });
});

QUnit.test("test center", function(assert) {
    this.$container.empty();
    var page = new Page.View({}).render();
    _check(assert, page, { left: "none", right: "none" });
});

QUnit.test("test left/center", function(assert) {
    this.$container.empty();
    var page = new Page.View({
        Left: Backbone.View.extend({
            initialize: function() {
                this.setElement($("<div/>"));
                this.model = new Backbone.Model({});
            }
        })
    }).render();
    _check(assert, page, { left: "block", right: "none" });
});
