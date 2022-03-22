/* global QUnit */
import $ from "jquery";
import sinon from "sinon";
import testApp from "../test-app";
import HDA_MODEL from "mvc/history/hda-model";

QUnit.module("History Contents Model QUnit.Tests", {
    beforeEach: function () {
        testApp.create();
    },
    afterEach: function () {
        testApp.destroy();
    },
});

QUnit.test("HDA Constructions with Default Attributes", function (assert) {
    var hda = new HDA_MODEL.HistoryDatasetAssociation({});
    assert.equal(hda.get("name"), "(unnamed dataset)");
    assert.equal(hda.get("state"), "new");
});

QUnit.test("HDA Construction with Supplied Attributes", function (assert) {
    var hda = new HDA_MODEL.HistoryDatasetAssociation({
        history_content_type: "dataset",
        name: "my dataset",
        state: "ok",
    });
    assert.equal(hda.get("name"), "my dataset");
    assert.equal(hda.get("state"), "ok");
});

QUnit.test("HDA Deletion", function (assert) {
    var hda = new HDA_MODEL.HistoryDatasetAssociation({
        history_content_type: "dataset",
        id: "hda1",
        history_id: "h1",
        deleted: false,
    });
    assert.equal(hda.get("deleted"), false);

    sinon.stub($, "ajax").yieldsTo("success", { deleted: true });
    hda["delete"]();
    // to get the url sinon used:
    //console.debug( $.ajax.lastCall.args[0].url )
    assert.ok($.ajax.calledWithMatch({ url: "/api/histories/h1/contents/datasets/hda1" }));
    assert.equal(hda.get("deleted"), true);
});
