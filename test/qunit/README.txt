Running Tests in qunit Directory
--------------------------------

From Command-line (with Grunt and Phantom):

 % npm install -g grunt-cli
 % npm install
 % grunt

To watch for changes to scripts and tests and automatically re-run tests:

 % grunt watch

You can limit the tests run to a single file using the test option (note:
that 'tests/' is prepended to the path):

 % grunt --test=metrics-logger.html
 (only testing tests/metrics-logger.html)

 % grunt watch --test=metrics-logger.html
 (only testing tests/metrics-logger.html)

From Web Browser (no additional dependencies):

  Just open test HTML file in Web Browser.

Note:
	The combination of requirejs and phantomjs used to load some of these
scripts can lead to error suppression. If any of the dependencies of the
scripts you're requiring throw an error, grunt+phantom+require will not
show a visible error (even with --verbose and/or --debug). You will instead
see a timeout error thrown from phantomjs.
    This generally(?) applies only to errors when evaluating the dependency.
