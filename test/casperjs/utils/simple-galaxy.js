/* Utility to load a specific page and output html, page text, or a screenshot
 *  Optionally wait for some time, text, or dom selector
 */
try {
    //...if there's a better way - please let me know, universe
    var scriptDir = require( 'system' ).args[3]
            // remove the script filename
            .replace( /[\w|\.|\-|_]*$/, '' )
            // if given rel. path, prepend the curr dir
            .replace( /^(?!\/)/, './' ),
        spaceghost = require( scriptDir + 'spaceghost' ).create({
            // script options here (can be overridden by CLI)
            //verbose: true,
            //logLevel: debug,
            scriptDir: scriptDir
        });


} catch( error ){
    console.debug( error );
    phantom.exit( 1 );
}

spaceghost.start();

// Use the --url to load a specific page (e.g. --url="http://localhost:8080/history")
spaceghost.thenOpen( spaceghost.baseUrl, function(){

    // options for waiting before output/screenshot:
    //      --waitMs=<some number of Ms> --> wait some number of Ms before output
    //      --waitForText=<some text> --> wait for some text to be rendered before output
    //      --waitForSelector=<css selector> --> wait for some DOM to be rendered before output
    if( 'waitMs' in spaceghost.cli.options ){
        spaceghost.wait( spaceghost.cli.get( 'waitMs' ) );

    } else if( 'waitForText' in spaceghost.cli.options ){
        spaceghost.waitForText( spaceghost.cli.get( 'waitForText' ) );

    } else if( 'waitForSelector' in spaceghost.cli.options ){
        spaceghost.waitForSelector( spaceghost.cli.get( 'waitForSelector' ) );
    }

    // --capture=<myscreenshot.png> --> capture a screenshot of the page
    // --html --> output the html of the page
    // (if not --html) --> output the text of the page
    spaceghost.then( function(){
        if( 'capture' in spaceghost.cli.options ){
            var sshotFilename = spaceghost.cli.get( 'capture' );
            spaceghost.debug( 'screenshot stored at: ' + sshotFilename );
            spaceghost.capture( sshotFilename );

        } else {
            if( spaceghost.cli.args.indexOf( 'html' ) != -1 ){
                spaceghost.debugHTML();

            } else {
                spaceghost.debugPage();
            }
        }
    });

});

spaceghost.run( function(){
});
