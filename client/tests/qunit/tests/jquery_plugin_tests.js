/* global QUnit */
import $ from "jquery";
import testApp from "../test-app";

QUnit.module("Galaxy jquery plugin test", {
    beforeEach: function () {
        testApp.create();
    },
    afterEach: function () {
        testApp.destroy();
    },
});

QUnit.test("Check jquery for tooltip and select2", function (assert) {
    assert.ok($.fn.tooltip);
    assert.ok($.fn.select2);
});
