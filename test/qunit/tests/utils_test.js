/* global define */
define([ 'test-app', 'utils/utils', "QUnit"
], function( testApp, Utils, QUnit ){
    'use strict';
    QUnit.module( 'Utils test', {} );

    QUnit.test( 'isEmpty', function(assert) {
        assert.ok( Utils.default.isEmpty( [] ), 'Empty array' );
        assert.ok( Utils.default.isEmpty( [ 'data', undefined ] ), 'Array contains `undefined`' );
        assert.ok( Utils.default.isEmpty( [ 'data', null ] ), 'Array contains `null`' );
        assert.ok( Utils.default.isEmpty( [ 'data', '__null__' ] ), 'Array contains `__null__`' );
        assert.ok( Utils.default.isEmpty( [ 'data', '__undefined__' ] ), 'Array contains `__undefined__`' );
        assert.ok( Utils.default.isEmpty( null ), 'Array is null' );
        assert.ok( Utils.default.isEmpty( '__null__' ), 'Array is __null__' );
        assert.ok( Utils.default.isEmpty( '__undefined__' ), 'Array is __undefined__' );
        assert.ok( !Utils.default.isEmpty( [ 'data' ] ), 'Array contains `data`' );
        assert.ok( !Utils.default.isEmpty( 1 ), 'Value is int' );
        assert.ok( !Utils.default.isEmpty( 0 ), 'Value is zero' );
    });
});