define([
    "galaxy",
    "jquery",
    "sinon-qunit"
], function(
    appBase,
    $,
    sinon
){
    /*globals equal test module expect deepEqual strictEqual throws ok */
    "use strict";

    module( "Galaxy client app tests" );

    var options = {
        config : {
            "allow_user_deletion": false,
            "allow_user_creation": true,
            "wiki_url": "https://wiki.galaxyproject.org/",
            "ftp_upload_site": null,
            "support_url": "https://wiki.galaxyproject.org/Support",
            "allow_user_dataset_purge": false,
            "allow_library_path_paste": false,
            "user_library_import_dir": null,
            "terms_url": null,
            "ftp_upload_dir": null,
            "library_import_dir": null,
            "logo_url": null,
            "enable_unique_workflow_defaults": false
        },
        user : {
            "username": "test",
            "quota_percent": null,
            "total_disk_usage": 61815527,
            "nice_total_disk_usage": "59.0 MB",
            "email": "test@test.test",
            "tags_used": [
              "test"
            ],
            "model_class": "User",
            "id": "f2db41e1fa331b3e"
        }
    };

    test( "App base construction/initializiation defaults", function() {
        var app = new appBase.GalaxyApp({});
        ok( app.hasOwnProperty( 'options' )     && typeof app.options === 'object' );
        ok( app.hasOwnProperty( 'logger' )      && typeof app.logger === 'object' );
        ok( app.hasOwnProperty( 'localize' )    && typeof app.localize === 'function' );
        ok( app.hasOwnProperty( 'config' )      && typeof app.config === 'object' );
        ok( app.hasOwnProperty( 'user' )        && typeof app.config === 'object' );

        // equal( true );
        equal( app.localize, window._l );
    });

    test( "App base default options", function() {
        var app = new appBase.GalaxyApp({});
        ok( app.hasOwnProperty( 'options' ) && typeof app.options === 'object' );
        equal( app.options.root,            '/' );
        equal( app.options.patchExisting,   true );
    });

    test( "App base extends from Backbone.Events", function() {
        var app = new appBase.GalaxyApp({});
        [ 'on', 'off', 'trigger', 'listenTo', 'stopListening' ].forEach( function( fn ){
            ok( app.hasOwnProperty( fn ) && typeof app[ fn ] === 'function' );
        });
    });

    test( "App base has logging methods from utils/add-logging.js", function() {
        var app = new appBase.GalaxyApp({});
        [ 'debug', 'info', 'warn', 'error', 'metric' ].forEach( function( fn ){
            ok( typeof app[ fn ] === 'function' );
        });
        ok( app._logNamespace === 'GalaxyApp' );
    });

    test( 'App base will patch in attributes from existing Galaxy objects', function(){
        window.Galaxy = {
            attribute : {
                subattr : 1
            }
        };
        var app = new appBase.GalaxyApp({});
        ok( typeof app.attribute === 'object' && app.attribute.subattr === 1 );
    });

    test( "App base logger", function() {
        var app = new appBase.GalaxyApp({});
        ok( app.hasOwnProperty( 'logger' ) && typeof app.config === 'object' );
    });

    test( "App base config", function() {
        var app = new appBase.GalaxyApp( options );
        ok( app.hasOwnProperty( 'config' ) && typeof app.config === 'object' );
        equal( app.config.allow_user_deletion,  false );
        equal( app.config.allow_user_creation,  true );
        equal( app.config.wiki_url,             "https://wiki.galaxyproject.org/" );
        equal( app.config.ftp_upload_site,      null );
        //...
    });

    test( "App base user", function() {
        var app = new appBase.GalaxyApp({});
        ok( app.hasOwnProperty( 'user' ) && typeof app.user === 'object' );
        ok( app.user.isAdmin() === false );
    });

});
