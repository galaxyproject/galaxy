// This file isn't really testing anything useful yet, it is just testing
// (or demonstrating) qunit+backbone interactions.
/* global define */
define([
    "mvc/history/hda-model",
    "mvc/history/hda-li",
    "jquery",
    "QUnit"
], function(
    HDA_MODEL,
    HDA_BASE,
    $,
    QUnit
){
    "use strict";
    HDA_MODEL = HDA_MODEL.default;
    HDA_BASE = HDA_BASE.default;
    QUnit.module( "HDA base backbone view tests" );

    QUnit.test( "Base HDA view default construction, initialize", function(assert) {
        var hda = new HDA_MODEL.HistoryDatasetAssociation({
                    id          : '123'
                }),
            view = new HDA_BASE.HDAListItemView({ model: hda });

        assert.strictEqual( view.model, hda );

        assert.equal( view.linkTarget, '_blank' );
        assert.equal( view.selectable, false );
        assert.equal( view.selected,   false );
        assert.equal( view.expanded,   false );
        assert.equal( view.draggable,  false );
        assert.equal( view.id(), 'dataset-123' );
    });
});
