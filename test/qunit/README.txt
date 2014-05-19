Running Tests in qunit Directory
--------------------------------

From Command-line (with Grunt and Phantom):

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

