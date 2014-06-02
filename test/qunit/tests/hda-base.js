// This file isn't really testing anything useful yet, it is just testing
// (or demonstrating) qunit+backbone interactions.
define([
    "mvc/dataset/hda-model",
    "mvc/dataset/hda-base",
    "jquery",
    "sinon-qunit",
    "utils/localization"
], function(
    hdaModel,
    hdaBase,
    $,
    sinon
){
    /*globals equal test module expect deepEqual strictEqual */
    "use strict";

    module( "HDA base backbone view tests" );

    test( "Base HDA view default construction, initialize", function() {
        var hda = new hdaModel.HistoryDatasetAssociation({
                    id          : '123'
                }),
            view = new hdaBase.HDABaseView({ model: hda });

        strictEqual( view.model, hda );

        equal( view.linkTarget, '_blank' );
        equal( view.selectable, false );
        equal( view.selected,   false );
        equal( view.expanded,   false );
        equal( view.draggable,  false );
        equal( view.id(), 'hda-123' );
    });
});
