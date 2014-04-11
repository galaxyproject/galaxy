// This file isn't really testing anything useful yet, it is just testing
// (or demonstrating) qunit+backbone interactions.
define([
    "utils/metrics-logger",
    "jquery",
    "sinon-qunit"
], function(
    metrics,
    $,
    sinon
){
    /*globals equal test module expect deepEqual strictEqual throws */
    "use strict";

    module( "Metrics logger tests" );

    test( "logger construction/initializiation defaults", function() {
        var logger = new metrics.MetricsLogger({});
        equal( logger.consoleLogger, null );
        equal( logger.options.logLevel,         metrics.MetricsLogger.INFO );
        equal( logger.options.consoleLevel,     metrics.MetricsLogger.NONE );
        equal( logger.options.defaultNamespace, 'Galaxy' );
        equal( logger.options.clientPrefix,     'client.' );
        equal( logger.options.postSize,         1000 );
        equal( logger.options.maxCacheSize,     3000 );
        equal( logger.options.addTime,          true );

        equal( logger._postSize, 1000 );
        equal( logger.cache.constructor, metrics.LoggingCache );
    });

    test( "_parseLevel", function() {
        var logger = new metrics.MetricsLogger({});
        equal( logger._parseLevel( 'all' ),     metrics.MetricsLogger.ALL );
        equal( logger._parseLevel( 'debug' ),   metrics.MetricsLogger.DEBUG );
        equal( logger._parseLevel( 'info' ),    metrics.MetricsLogger.INFO );
        equal( logger._parseLevel( 'warn' ),    metrics.MetricsLogger.WARN );
        equal( logger._parseLevel( 'error' ),   metrics.MetricsLogger.ERROR );
        equal( logger._parseLevel( 'metric' ),  metrics.MetricsLogger.METRIC );
        equal( logger._parseLevel( 'none' ),    metrics.MetricsLogger.NONE );
        equal( logger._parseLevel( 15 ),        15 );

        throws( function(){
            logger._parseLevel( undefined );
        }, /Unknown log level/, 'Unknown log level throws error' );
        throws( function(){
            logger._parseLevel( 'nope' );
        }, /Unknown log level/, 'Unknown log level throws error' );
    });
    
    test( "cache construction/initializiation defaults", function() {
        var cache = new metrics.LoggingCache();
        equal( cache.maxSize,   5000 );
        equal( $.type( cache._cache ), 'array' );
    });
});
