var gulp = require('gulp');

var babel = require('gulp-babel');
var del = require('del');
var sourcemaps = require('gulp-sourcemaps');
var uglify = require('gulp-uglify');
var cached = require('gulp-cached');

var paths = {
    scripts: ['galaxy/scripts/**/*.js',
              '!galaxy/scripts/apps/**/*.js',
               '!galaxy/scripts/libs/**/*.js'
    ],
    libs: ['galaxy/scripts/libs/**/*.js']
};

gulp.task('scripts', function() {
  return gulp.src(paths.scripts)
    .pipe(cached('scripts'))
    .pipe(sourcemaps.init())
    .pipe(babel())
    .pipe(uglify())
    .pipe(sourcemaps.write('../maps/'))
    .pipe(gulp.dest('../static/scripts/'));
});

gulp.task('libs', function() {
  return gulp.src(paths.libs)
    .pipe(uglify())
    .pipe(gulp.dest('../static/scripts/libs/'));
});

gulp.task('clean', function(){
    //Wipe out all scripts that aren't handled by webpack
    return del(['../static/scripts/**/*.js',
                '!../static/scripts/bundled/**.*.js'],
               {force: true});
});

gulp.task('watch', function(){
    gulp.watch(paths.scripts, ['scripts']);
});

gulp.task('default', ['scripts', 'libs']);
