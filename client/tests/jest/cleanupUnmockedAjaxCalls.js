const flushPromises = require("flush-promises");

// The current tests are horrible, unresolved promises that error out can
// ruin subsequent tests.
module.exports = async () => {
    console.log("promises flushed");
    await flushPromises();
}
