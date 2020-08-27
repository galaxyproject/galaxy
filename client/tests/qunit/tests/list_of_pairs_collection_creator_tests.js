/* global QUnit */
import _ from "underscore";
import $ from "jquery";
// import sinon from "sinon";
import testApp from "../test-app";
import PAIRED_COLLECTION_CREATOR from "mvc/collection/list-of-pairs-collection-creator";
import DATA from "../test-data/paired-collection-creator.data";

var PCC = PAIRED_COLLECTION_CREATOR.PairedCollectionCreator;

QUnit.module("Galaxy client app tests", {
    beforeEach: function () {
        testApp.create();
        $.fx.off = true;
    },
    afterEach: function () {
        testApp.destroy();
        $.fx.off = false;
    },
});

QUnit.test("Creator base/empty construction/initializiation defaults", function (assert) {
    var pcc = new PCC([]);
    assert.ok(pcc instanceof PCC);
    assert.deepEqual(pcc.filters, pcc.commonFilters[pcc.DEFAULT_FILTERS]);
    assert.ok(pcc.automaticallyPair);
    assert.equal(pcc.matchPercentage, 0.9);
    assert.equal(pcc.strategy, "autopairLCS");
});

QUnit.test("Creator construction/initializiation with datasets", function (assert) {
    var pcc = new PCC({
        datasets: DATA._1,
    });
    // pcc maintains the original list - which, in this case, is already sorted
    assert.deepEqual(pcc.initialList, DATA._1);
    // datasets 1 has no ids, so the pcc will create them
    assert.ok(
        _.every(pcc.initialList, function (dataset) {
            return dataset.id;
        })
    );
    // datasets 1 is very easy to auto pair
    assert.equal(pcc.unpaired.length, 0);
    assert.equal(pcc.paired.length, pcc.initialList.length / 2);
});

QUnit.test("Try easy autopairing with simple exact matching", function (assert) {
    var pcc = new PCC({
        datasets: DATA._1,
        strategy: "simple",
        twoPassAutopairing: false,
    });
    assert.equal(pcc.unpaired.length, 0);
    assert.equal(pcc.paired.length, pcc.initialList.length / 2);
});

QUnit.test("Try easy autopairing with LCS", function (assert) {
    var pcc = new PCC({
        datasets: DATA._1,
        strategy: "lcs",
        twoPassAutopairing: false,
    });
    assert.equal(pcc.unpaired.length, 0);
    assert.equal(pcc.paired.length, pcc.initialList.length / 2);
});

QUnit.test("Try easy autopairing with Levenshtein", function (assert) {
    var pcc = new PCC({
        datasets: DATA._1,
        strategy: "levenshtein",
        twoPassAutopairing: false,
    });
    assert.equal(pcc.unpaired.length, 0);
    assert.equal(pcc.paired.length, pcc.initialList.length / 2);
});
