// This file isn't really testing anything useful yet, it is just testing
// (or demonstrating) qunit+backbone interactions.

/* global QUnit */
import testApp from "../test-app";
import HDA_MODEL from "mvc/history/hda-model";
import HDA_BASE from "mvc/history/hda-li";

QUnit.module("HDA base backbone view tests", {
    beforeEach: function () {
        testApp.create();
    },
    afterEach: function () {
        testApp.destroy();
    },
});

QUnit.test("Base HDA view default construction, initialize", function (assert) {
    var hda = new HDA_MODEL.HistoryDatasetAssociation({
            id: "123",
        }),
        view = new HDA_BASE.HDAListItemView({ model: hda });

    assert.strictEqual(view.model, hda);

    assert.equal(view.linkTarget, "_blank");
    assert.equal(view.selectable, false);
    assert.equal(view.selected, false);
    assert.equal(view.expanded, false);
    assert.equal(view.draggable, false);
    assert.equal(view.id(), "dataset-123");
});
