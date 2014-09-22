// This file isn't really testing anything useful yet, it is just testing
// (or demonstrating) qunit+backbone interactions.
define([
    "mvc/history/hda-model",
    "mvc/history/hda-li",
    "jquery",
    "sinon-qunit"
], function(
    HDA_MODEL,
    HDA_BASE,
    $,
    sinon
){
    /*globals equal test module expect deepEqual strictEqual */
    "use strict";

    module( "HDA base backbone view tests" );

    test( "Base HDA view default construction, initialize", function() {
        var hda = new HDA_MODEL.HistoryDatasetAssociation({
                    id          : '123'
                }),
            view = new HDA_BASE.HDAListItemView({ model: hda });

        strictEqual( view.model, hda );

        equal( view.linkTarget, '_blank' );
        equal( view.selectable, false );
        equal( view.selected,   false );
        equal( view.expanded,   false );
        equal( view.draggable,  false );
        equal( view.id(), 'dataset-123' );
    });
});
