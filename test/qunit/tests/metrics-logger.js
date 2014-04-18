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
    /*globals equal test module expect deepEqual strictEqual throws ok */
    "use strict";

    var MockConsole = function(){
        var self = this;
        self.lastMessage = null;
        [ 'log', 'debug', 'info', 'warn', 'error' ].forEach( function( fnName ){
            self[ fnName ] = function(){
                self.lastMessage = { level: fnName, args: Array.prototype.slice.call( arguments, 0 ) };
            };
        });
    };

    module( "Metrics logger tests" );

    // ======================================================================== MetricsLogger
    test( "logger construction/initializiation defaults", function() {
        var logger = new metrics.MetricsLogger({});
        equal( logger.consoleLogger, null );
        equal( logger.options.logLevel,         metrics.MetricsLogger.NONE );
        equal( logger.options.consoleLevel,     metrics.MetricsLogger.NONE );
        equal( logger.options.defaultNamespace, 'Galaxy' );
        equal( logger.options.clientPrefix,     'client.' );
        equal( logger.options.postSize,         1000 );
        equal( logger.options.maxCacheSize,     3000 );
        equal( logger.options.addTime,          true );
        equal( logger.options.postUrl,          '/api/metrics' );
        equal( logger.options.getPingData,      undefined );
        equal( logger.options.onServerResponse, undefined );

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

    // ------------------------------------------------------------------------ Emit to cache
    test( "emit to cache at level", function() {
        var logger = new metrics.MetricsLogger({
            logLevel : 'metric'
        });
        equal( logger.options.logLevel, metrics.MetricsLogger.METRIC );
        logger.emit( 'metric', 'test', [ 1, 2, { three: 3 }] );
        equal( logger.cache.length(), 1 );

        var cached = JSON.parse( logger.cache.get( 1 ) );
        equal( cached.level, metrics.MetricsLogger.METRIC );
        equal( cached.namespace, 'client.test' );
        equal( cached.args.length, 3 );
        equal( cached.args[2].three, 3 );
        ok( typeof cached.time === 'string' );
        ok( cached.time === new Date( cached.time ).toISOString() );
    });

    test( "emit to cache below does not cache", function() {
        var logger = new metrics.MetricsLogger({
            logLevel : 'metric'
        });
        logger.emit( 'error', 'test', [ 1, 2, { three: 3 }] );
        equal( logger.cache.length(), 0 );
    });

    test( "emit to cache (silently) drops non-parsable", function() {
        var logger = new metrics.MetricsLogger({
            logLevel : 'metric'
        });
        logger.emit( 'metric', 'test', [{ window: window }] );
        equal( logger.cache.length(), 0 );
    });
    
    // ======================================================================== LoggingCache
    test( "cache construction/initializiation defaults", function() {
        var cache = new metrics.LoggingCache();
        equal( cache.maxSize,   5000 );
        equal( $.type( cache._cache ), 'array' );
    });

    test( "cache construction/initializiation setting max cache size", function() {
        var cache = new metrics.LoggingCache({
            maxSize : 5
        });
        equal( cache.maxSize, 5 );
    });

    test( "cache plays well with no data", function() {
        var cache = new metrics.LoggingCache();

        equal( cache._cache.length, 0 );
        equal( cache.length(), 0 );
        var get = cache.get( 10 );
        ok( jQuery.type( get ) === 'array' && get.length === 0 );
        var remove = cache.remove( 10 );
        ok( jQuery.type( remove ) === 'array' && remove.length === 0 );
        equal( cache.length(), 0 );
    });

    test( "cache add properly adds and removes data", function() {
        var cache = new metrics.LoggingCache({
            maxSize : 5
        });
        var entry1 = [{ one: 1 }, 'two' ];
        cache.add( entry1 );

        equal( cache._cache.length, 1 );
        equal( cache.length(), 1 );
        equal( cache._cache[0], JSON.stringify( entry1 ) );
        equal( cache.get( 1 ), JSON.stringify( entry1 ) );

        var entry2 = { blah: { one: 1 }, bler: [ 'three', { two: 2 } ] };
        cache.add( entry2 );
        equal( cache.length(), 2 );
        equal( cache.stringify( 2 ), '[\n' + JSON.stringify( entry1 ) + ',\n' + JSON.stringify( entry2 ) + '\n]' );

        // FIFO
        var returned = cache.remove( 1 );
        equal( cache.length(), 1 );
        ok( jQuery.type( returned ) === 'array' && returned.length === 1 );
        var returned0 = returned[0];
        ok( jQuery.type( returned0 ) === 'string' && returned0 === JSON.stringify( entry1 ) );
    });

    test( "cache past max loses oldest", function() {
        var cache = new metrics.LoggingCache({
            maxSize : 5
        });
        for( var i=0; i<10; i+=1 ){
            cache.add({ index: i });
        }
        equal( cache.length(), 5 );
        var get = cache.get( 5 );
        ok( JSON.parse( get[0] ).index === 5 );
        ok( JSON.parse( get[1] ).index === 6 );
        ok( JSON.parse( get[2] ).index === 7 );
        ok( JSON.parse( get[3] ).index === 8 );
        ok( JSON.parse( get[4] ).index === 9 );
    });
});
