var pathname = location.pathname;
var qunit_absolute_directory = pathname.substring( 0, pathname.lastIndexOf( "qunit/" ) + 6 );
var filename = pathname.substr( pathname.lastIndexOf( "/" ) + 1 );

// Configure require.js for unit testing.
require.config({
    baseUrl: qunit_absolute_directory + "scripts",
    paths: {
        // Custom paths for Galaxy dependencies...
        "jquery": "libs/jquery/jquery",
        "backbone": "libs/backbone/backbone",
        "underscore": "libs/underscore",
        // Custom paths for qunit testing dependencies...
        "QUnit": qunit_absolute_directory + "test-libs/qunit-1.14.0", // .. because baseUrl is scripts to match Galaxy.
        "sinon": qunit_absolute_directory + "test-libs/sinon-1.9.1",
        "sinon-qunit": qunit_absolute_directory + "test-libs/sinon-qunit-1.0.0"
    },
    shim: {
        // Ensure correct Qunit order in light of requirejs loading...
        // https://gist.github.com/drewwells/920405
        "QUnit": {
            exports: "QUnit",
            init: function() {
                QUnit.config.autostart = false;
                bridge_phantomjs( QUnit );
            }
        },
        "sinon": {
            exports: "sinon"
        },
        "sinon-qunit": {
            deps: [ 'sinon', "QUnit" ],
            exports: "sinon"  // Odd but seems to work
        },
        "underscore": {
            exports: "_"
        },
        "backbone": {
            deps: [ 'underscore', 'jquery' ],
            exports: "Backbone"
        }
    }
} );

// Mock out Galaxy globals.
var galaxy_config =
{
    root: '/'
};

require( [ "jquery", "QUnit" ], function( $, QUnit ) {
    // Bootstrap HTML for displaying Qunit results.
    $('head').append( $('<link rel="stylesheet" type="text/css"  />')
        .attr( "href", qunit_absolute_directory + "test-libs/qunit-1.14.0.css") );
    $('body').append( $('<div id="qunit">') );
    $('body').append( $('<div id="qunit-fixture">') );

    var test_module_path = "./" + filename.replace( ".html", ".js" );

    // underscore + backbone loaded here because they are assumed globals by
    // much of the Galaxy client code.
    require( [ "underscore", "backbone" ], function( _, Backbone ) {
        require( [ test_module_path ], function( ) {
            QUnit.load();
            QUnit.start();
        } );

    } );

});



function bridge_phantomjs( QUnit ) {
    // Needed because the grunt task will attempt to inject this bridge assuming
    // QUnit is loaded directly - not using require.js.
    // https://github.com/gruntjs/grunt-contrib-qunit/blob/master/phantomjs/bridge.js
    var userAgent = navigator && navigator.userAgent;
    if( ! userAgent || userAgent.indexOf( "PhantomJS" ) < 0 ) {
        return;
    }

    /*global QUnit:true, alert:true*/
    (function () {
      'use strict';
      console.log(  );
      // Don't re-order tests.
      // QUnit.config.reorder = false;

      // Send messages to the parent PhantomJS process via alert! Good times!!
      function sendMessage() {
        var args = [].slice.call(arguments);
        alert(JSON.stringify(args));
      }
      
      // These methods connect QUnit to PhantomJS.
      QUnit.log(function(obj) {
        // What is this I don’t even
        if (obj.message === '[object Object], undefined:undefined') { return; }
        // Parse some stuff before sending it.
        var actual = QUnit.jsDump.parse(obj.actual);
        var expected = QUnit.jsDump.parse(obj.expected);
        // Send it.
        sendMessage('qunit.log', obj.result, actual, expected, obj.message, obj.source);
      });

      QUnit.testStart(function(obj) {
        sendMessage('qunit.testStart', obj.name);
      });

      QUnit.testDone(function(obj) {
        sendMessage('qunit.testDone', obj.name, obj.failed, obj.passed, obj.total);
      });

      QUnit.moduleStart(function(obj) {
        sendMessage('qunit.moduleStart', obj.name);
      });

      QUnit.moduleDone(function(obj) {
        sendMessage('qunit.moduleDone', obj.name, obj.failed, obj.passed, obj.total);
      });

      QUnit.begin(function() {
        sendMessage('qunit.begin');
      });

      QUnit.done(function(obj) {
        sendMessage('qunit.done', obj.failed, obj.passed, obj.total, obj.runtime);
      });
    }());
}
