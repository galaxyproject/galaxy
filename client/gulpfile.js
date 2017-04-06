var gulp = require('gulp');
var uglify = require('gulp-uglify');
var sourcemaps = require('gulp-sourcemaps');
var del = require('del');

var paths = {
    scripts: ['galaxy/scripts/**/*.js',
              '!galaxy/scripts/apps/**/*.js'
    ]
};

gulp.task('scripts', ['clean'], function() {
  return gulp.src(paths.scripts)
    .pipe(sourcemaps.init())
    // Transpile here prior to uglify.
    .pipe(uglify())
    .pipe(sourcemaps.write('../maps/'))
    .pipe(gulp.dest('../static/scripts/'));
});

gulp.task('clean', function(){
    //Wipe out all scripts that aren't handled by webpack
    return del(['../static/scripts/**/*.js',
                '!../static/scripts/bundled/**.*.js'],
               {force: true});
});

gulp.task('default', ['scripts']);
