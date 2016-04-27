/* global define, QUnit, module, test, ok, equal, deepEqual, notEqual */
define([ 'test-app', 'utils/utils',
], function( testApp, Utils ){
    'use strict';
    module( 'Utils test', {} );

    test( 'isEmpty', function() {
        ok( Utils.isEmpty( [] ), 'Empty array' );
        ok( Utils.isEmpty( [ 'data', undefined ] ), 'Array contains `undefined`' );
        ok( Utils.isEmpty( [ 'data', null ] ), 'Array contains `null`' );
        ok( Utils.isEmpty( [ 'data', '__null__' ] ), 'Array contains `__null__`' );
        ok( Utils.isEmpty( [ 'data', '__undefined__' ] ), 'Array contains `__undefined__`' );
        ok( Utils.isEmpty( null ), 'Array is null' );
        ok( Utils.isEmpty( '__null__' ), 'Array is __null__' );
        ok( Utils.isEmpty( '__undefined__' ), 'Array is __undefined__' );
        ok( !Utils.isEmpty( [ 'data' ] ), 'Array contains `data`' );
        ok( !Utils.isEmpty( 1 ), 'Value is int' );
        ok( !Utils.isEmpty( 0 ), 'Value is zero' );
    });
});