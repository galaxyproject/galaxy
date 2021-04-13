// For testing, bypass the worker convrsions
// and wrap each function in a jest mock wrapper

const cacheapi = require("../CacheApi");

const mockedModule = Object.entries(cacheapi).reduce((mod, [fnName, orig]) => {
    return { ...mod, [fnName]: jest.fn(orig) };
}, {});

module.exports = mockedModule;
