// This file isn't really testing anything useful yet, it is just testing
// (or demonstrating) qunit+backbone interactions.
/* global define */
import testApp from "qunit/test-app";
import HDA_MODEL from "mvc/history/hda-model";
import HDA_BASE from "mvc/history/hda-li";
import $ from "jquery";

QUnit.module("HDA base backbone view tests");

QUnit.test("Base HDA view default construction, initialize", function(assert) {
    var hda = new HDA_MODEL.HistoryDatasetAssociation({
            id: "123"
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
