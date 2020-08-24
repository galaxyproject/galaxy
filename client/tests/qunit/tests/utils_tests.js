/* global QUnit */
import testApp from "../test-app";
import Utils from "utils/utils";

QUnit.module("Utils test", {
    beforeEach: function () {
        testApp.create();
    },
    afterEach: function () {
        testApp.destroy();
    },
});

QUnit.test("isEmpty", function (assert) {
    assert.ok(Utils.isEmpty([]), "Empty array");
    assert.ok(Utils.isEmpty(["data", undefined]), "Array contains `undefined`");
    assert.ok(Utils.isEmpty(["data", null]), "Array contains `null`");
    assert.ok(Utils.isEmpty(["data", "__null__"]), "Array contains `__null__`");
    assert.ok(Utils.isEmpty(["data", "__undefined__"]), "Array contains `__undefined__`");
    assert.ok(Utils.isEmpty(null), "Array is null");
    assert.ok(Utils.isEmpty("__null__"), "Array is __null__");
    assert.ok(Utils.isEmpty("__undefined__"), "Array is __undefined__");
    assert.ok(!Utils.isEmpty(["data"]), "Array contains `data`");
    assert.ok(!Utils.isEmpty(1), "Value is int");
    assert.ok(!Utils.isEmpty(0), "Value is zero");
});
