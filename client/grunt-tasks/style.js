/**
 * Grunt task to build static/style resources (css, sprites)
 * @param  {Object} grunt main grunt file
 * @return {Function} callback to build this task
 */
module.exports = function( grunt ){
    "use strict";

    var _ = grunt.util._,
        fmt = _.sprintf,
    	theme = grunt.option( 'theme', 'blue' ),
        styleDistPath = '../static/style/blue',
        imagesPath = '../static/images',
        lessPath = './galaxy/style/less',
        lessFiles = [
            'base',
            'autocomplete_tagging',
            'embed_item',
            'iphone',
            'library',
            'trackster',
            'circster',
            'reports'
        ];


    // Create sprite images and .less files
    grunt.config( 'sprite', {
        options: {
            algorithm: 'binary-tree'
        },
        'history-buttons': {
            src: fmt( '%s/history-buttons/*.png', imagesPath ),
            dest: fmt( '%s/sprite-history-buttons.png', styleDistPath ),
            imgPath: fmt( 'sprite-history-buttons.png' ),
            destCss: fmt( '%s/sprite-history-buttons.less', lessPath )
        },
        'history-states': {
            src: fmt( '%s/history-states/*.png', imagesPath ),
            dest: fmt( '%s/sprite-history-states.png', styleDistPath ),
            imgPath: fmt( 'sprite-history-states.png' ),
            destCss: fmt( '%s/sprite-history-states.less', lessPath )
        },
        'fugue': {
            src: fmt( '%s/fugue/*.png', imagesPath ),
            dest: fmt( '%s/sprite-fugue.png', styleDistPath ),
            imgPath: fmt( 'sprite-fugue.png' ),
            destCss: fmt( '%s/sprite-fugue.less', lessPath )
        }
    });

    // Compile less files
    grunt.config( 'less', {
        options: {
            compress: true,
            paths: [ lessPath ],
            strictImports: true
        },
        dist: {
            files: _.reduce( lessFiles, function( d, s ) {
                var output = fmt( '%s/%s.css', styleDistPath, s ),
                    input = fmt( '%s/%s.less', lessPath, s );
                d[ output ] = [ input ]; return d;
            }, {} )
        }
    });

    // remove tmp files
    grunt.config( 'clean', {
        options : {
            force: true
        },
        clean : [
            fmt( '%s/tmp-site-config.less', lessPath )
        ]
    });


    // -------------------------------------------------------------------------- watch & rebuild less files
    // use 'grunt watch-style' (from a new tab in your terminal) to have grunt re-copy changed files automatically
    //
    // the conditional prevents reconfiguration of 'normal' (.js) grunt watch from grunt-tasks/scripts.js

    if (this.cli.tasks.indexOf("watch-style") > -1){
        grunt.config( 'watch', {
            watch: {
                // watch for changes in the src dir
                files: [ lessPath + '/**' ],
                tasks: ['check-modules', 'sprite', 'less-site-config', 'less', 'clean'],
                options: {
                    spawn: false
                }
            }
        });
    }

    grunt.loadNpmTasks( 'grunt-contrib-less' );
    grunt.loadNpmTasks( 'grunt-spritesmith' );
    grunt.loadNpmTasks( 'grunt-contrib-clean' );
    grunt.loadNpmTasks( 'grunt-contrib-watch' );

    // Write theme variable for less
    grunt.registerTask( 'less-site-config', 'Write site configuration for less', function() {
        grunt.file.write( fmt( '%s/tmp-site-config.less', lessPath ), fmt( "@theme-name: %s;", theme ) );
    });

    grunt.registerTask( 'watch-style', [ 'watch' ] );
    grunt.registerTask( 'style', [  'check-modules', 'sprite', 'less-site-config', 'less', 'clean' ] );
};
