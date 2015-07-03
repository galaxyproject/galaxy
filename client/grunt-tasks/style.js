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
            'masthead',
            'library',
            'trackster',
            'circster'
        ];


    // Create sprite images and .less files
    grunt.config( 'sprite', {
        options: {
            algorithm: 'binary-tree'
        },
        'history-buttons': {
            src: fmt( '%s/history-buttons/*.png', imagesPath ),
            destImg: fmt( '%s/sprite-history-buttons.png', styleDistPath ),
            imgPath: fmt( 'sprite-history-buttons.png' ),
            destCSS: fmt( '%s/sprite-history-buttons.less', lessPath )
        },
        'history-states': {
            src: fmt( '%s/history-states/*.png', imagesPath ),
            destImg: fmt( '%s/sprite-history-states.png', styleDistPath ),
            imgPath: fmt( 'sprite-history-states.png' ),
            destCSS: fmt( '%s/sprite-history-states.less', lessPath )
        },
        'fugue': {
            src: fmt( '%s/fugue/*.png', imagesPath ),
            destImg: fmt( '%s/sprite-fugue.png', styleDistPath ),
            imgPath: fmt( 'sprite-fugue.png' ),
            destCSS: fmt( '%s/sprite-fugue.less', lessPath )
        }
    });

    // Compile less files
    grunt.config( 'less', {
        options: {
            compress: true,
            paths: [ styleDistPath ]
        },
        dist: {
            files: _.reduce( lessFiles, function( d, s ) {
                d[ fmt( '%s/%s.css', styleDistPath, s ) ] = [ fmt( '%s/%s.less', lessPath, s ) ]; return d;
            }, {} )
        }
    });

    // remove tmp files
    grunt.config( 'clean', {
        clean : [
            fmt( '%s/tmp-site-config.less', lessPath )
        ]
    });

    grunt.loadNpmTasks( 'grunt-contrib-less' );
    grunt.loadNpmTasks( 'grunt-spritesmith' );
    grunt.loadNpmTasks( 'grunt-contrib-clean' );

    // Write theme variable for less
    grunt.registerTask( 'less-site-config', 'Write site configuration for less', function() {
        grunt.file.write( fmt( '%s/tmp-site-config.less', lessPath ), fmt( "@theme-name: %s;", theme ) );
    });

    grunt.registerTask( 'style', [ 'sprite', 'less-site-config', 'less', 'clean' ] );
};