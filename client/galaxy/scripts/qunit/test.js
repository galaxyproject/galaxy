// Load all qunit tests into a single bundle.
var testsContext = require.context(".", true, /_tests$/);
testsContext.keys().forEach(testsContext);
