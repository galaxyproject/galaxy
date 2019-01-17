/**
 * A combination of all the mocha test files so that we can run them as a unit,
 * which is much faster during deployment.
 *
 * Note, this is non-intuitive, but the parameters of require.context must be
 * literals, can't even be stored in local variables or webpack can't do static
 * dependency analysis.
 *
 * https://webpack.js.org/guides/dependency-management/
 */
// eslint-disable-next-line no-undef
let testContext = require.context("./", true, /\.test\.js$/);
testContext.keys().forEach(testContext);
