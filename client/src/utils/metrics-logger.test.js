// This file isn't really testing anything useful yet, it is just testing
// (or demonstrating) qunit+backbone interactions.

import jQuery from "jquery";
import sinon from "sinon";
import metrics from "utils/metrics-logger";

const MockConsole = function () {
    this.lastMessage = null;
    ["log", "debug", "info", "warn", "error"].forEach((fnName) => {
        this[fnName] = function () {
            var args = Array.prototype.slice.call(arguments, 0);
            this.lastMessage = { level: fnName, args: args };
        };
    });
    return this;
};

describe("metrics-logger tests", function () {
    test("logger construction/initializiation defaults", function () {
        const logger = new metrics.MetricsLogger({});
        expect(logger.consoleLogger).toEqual(null);
        expect(logger.options.logLevel).toEqual(metrics.MetricsLogger.NONE);
        expect(logger.options.consoleLevel).toEqual(metrics.MetricsLogger.NONE);
        expect(logger.options.defaultNamespace).toEqual("Galaxy");
        expect(logger.options.clientPrefix).toEqual("client.");
        expect(logger.options.postSize).toEqual(1000);
        expect(logger.options.maxCacheSize).toEqual(3000);
        expect(logger.options.addTime).toEqual(true);
        expect(logger.options.postUrl).toEqual("/api/metrics");
        expect(logger.options.getPingData).toEqual(undefined);
        expect(logger.options.onServerResponse).toEqual(undefined);

        expect(logger._postSize).toEqual(1000);
        expect(logger.cache.constructor).toEqual(metrics.LoggingCache);
    });

    test("_parseLevel", function () {
        const logger = new metrics.MetricsLogger({});
        expect(logger._parseLevel("all")).toEqual(metrics.MetricsLogger.ALL);
        expect(logger._parseLevel("debug")).toEqual(metrics.MetricsLogger.DEBUG);
        expect(logger._parseLevel("info")).toEqual(metrics.MetricsLogger.INFO);
        expect(logger._parseLevel("warn")).toEqual(metrics.MetricsLogger.WARN);
        expect(logger._parseLevel("error")).toEqual(metrics.MetricsLogger.ERROR);
        expect(logger._parseLevel("metric")).toEqual(metrics.MetricsLogger.METRIC);
        expect(logger._parseLevel("none")).toEqual(metrics.MetricsLogger.NONE);
        expect(logger._parseLevel(15)).toEqual(15);
        //
        expect(() => {
            logger._parseLevel(undefined);
        }).toThrowError(/Unknown log level/);
        expect(() => {
            logger._parseLevel("nope");
        }).toThrowError(/Unknown log level/);
    });

    test("emit to cache at level", function () {
        const logger = new metrics.MetricsLogger({
            logLevel: "metric",
        });
        logger.cache.empty();

        expect(logger.options.logLevel).toEqual(metrics.MetricsLogger.METRIC);
        logger.emit("metric", "test", [1, 2, { three: 3 }]);
        expect(logger.cache.length()).toEqual(1);

        const cached = logger.cache.get(1)[0];
        expect(cached.level).toEqual(metrics.MetricsLogger.METRIC);
        expect(cached.namespace).toEqual("client.test");
        expect(cached.args.length).toEqual(3);
        expect(cached.args[2].three).toEqual(3);
        expect(typeof cached.time === "string").toBeTruthy();
        expect(cached.time === new Date(cached.time).toISOString());
    });

    test("emit to cache below does not cache", function () {
        const logger = new metrics.MetricsLogger({
            logLevel: "metric",
        });
        logger.cache.empty();

        logger.emit("error", "test", [1, 2, { three: 3 }]);
        expect(logger.cache.length()).toBe(0);
    });

    test("emit to cache (silently) drops non-parsable", function () {
        const logger = new metrics.MetricsLogger({
            logLevel: "metric",
        });
        logger.cache.empty();

        logger.emit("metric", "test", [{ window: window }]);
        expect(logger.cache.length()).toBe(0);
    });

    // function metricsFromRequestBody(request) {
    //     // assumes 'metrics' is only entry in requestBody
    //     return JSON.parse(decodeURIComponent(request.requestBody.replace("metrics=", "")));
    // }

    // QUnit.test("_postCache success", function (assert) {
    //     var callback = sinon.spy(),
    //         logger = new metrics.MetricsLogger({
    //             logLevel: "metric",
    //             onServerResponse: function (response) {
    //                 callback();
    //             },
    //         });
    //     logger.cache.empty();

    //     var server = sinon.fakeServer.create(),
    //         metricsOnServer;
    //     server.respondWith("POST", "/api/metrics", function (request) {
    //         metricsOnServer = metricsFromRequestBody(request);
    //         //console.debug( 'requestBody:', request.requestBody );
    //         //console.debug( 'metricsOnServer:', JSON.stringify( metricsOnServer, null, '  ' ) );
    //         request.respond(
    //             200,
    //             { "Content-Type": "application/json" },
    //             JSON.stringify({
    //                 fakeResponse: "yes",
    //             })
    //         );
    //     });

    //     logger.emit("metric", "test", [1, 2, { three: 3 }]);
    //     logger._postCache();
    //     server.respond();

    //     assert.ok(callback.calledOnce, "onServerResponse was called");
    //     assert.equal(logger.cache.length(), 0, "should have emptied cache (on success)");
    //     assert.equal(logger._postSize, 1000, "_postSize still at default");

    //     // metrics were in proper form on server
    //     assert.equal(metricsOnServer.length, 1);
    //     var metric = metricsOnServer[0];
    //     assert.equal(metric.level, metrics.MetricsLogger.METRIC);
    //     assert.equal(metric.namespace, "client.test");
    //     assert.equal(metric.args.length, 3);
    //     assert.equal(metric.args[2].three, 3);
    //     assert.ok(typeof metric.time === "string");
    //     assert.ok(metric.time === new Date(metric.time).toISOString());

    //     server.restore();
    // });

    // QUnit.test("_postCache failure", function (assert) {
    //     var callback = sinon.spy(),
    //         logger = new metrics.MetricsLogger({
    //             logLevel: "metric",
    //             onServerResponse: function (response) {
    //                 callback();
    //             },
    //         });
    //     logger.cache.empty();

    //     var server = sinon.fakeServer.create();
    //     server.respondWith("POST", "/api/metrics", function (request) {
    //         request.respond(
    //             500,
    //             { "Content-Type": "application/json" },
    //             JSON.stringify({
    //                 err_msg: "NoooOPE!",
    //             })
    //         );
    //     });

    //     logger.emit("metric", "test", [1, 2, { three: 3 }]);
    //     logger._postCache();
    //     server.respond();
    //     //TODO: is the following what we want?
    //     assert.ok(!callback.calledOnce, "onServerResponse was NOT called");
    //     assert.equal(logger.cache.length(), 1, "should NOT have emptied cache");
    //     assert.equal(logger._postSize, logger.options.maxCacheSize, "_postSize changed to max");

    //     server.restore();
    // });

    // // ------------------------------------------------------------------------ Emit to console
    // QUnit.test("emit to console at level", function (assert) {
    //     var mockConsole = new MockConsole(),
    //         logger = new metrics.MetricsLogger({
    //             consoleLevel: "debug",
    //             consoleLogger: mockConsole,
    //         });
    //     assert.equal(logger.options.consoleLevel, metrics.MetricsLogger.DEBUG);
    //     assert.equal(logger.consoleLogger.constructor, MockConsole);

    //     logger.emit("debug", "test", [1, 2, { three: 3 }]);
    //     assert.equal(logger.cache.length(), 1);
    //     //console.debug( JSON.stringify( mockConsole.lastMessage ) );
    //     assert.equal(mockConsole.lastMessage.level, "debug");
    //     assert.equal(mockConsole.lastMessage.args.length, 4);
    //     assert.equal(mockConsole.lastMessage.args[0], "test");
    //     assert.equal(mockConsole.lastMessage.args[3].three, 3);
    // });

    // QUnit.test("emit to console below does not output", function (assert) {
    //     var mockConsole = new MockConsole(),
    //         logger = new metrics.MetricsLogger({
    //             consoleLevel: "error",
    //             consoleLogger: mockConsole,
    //         });
    //     logger.emit("debug", "test", [1, 2, { three: 3 }]);
    //     assert.equal(mockConsole.lastMessage, null);
    // });

    // // ------------------------------------------------------------------------ Shortcuts
    // QUnit.test("logger shortcuts emit to default namespace properly", function (assert) {
    //     var logger = new metrics.MetricsLogger({
    //         logLevel: "all",
    //     });
    //     logger.cache.empty();

    //     assert.equal(logger.options.logLevel, metrics.MetricsLogger.ALL);
    //     logger.log(0);
    //     logger.debug(1);
    //     logger.info(2);
    //     logger.warn(3);
    //     logger.error(4);
    //     logger.metric(5);

    //     assert.equal(logger.cache.length(), 6);
    //     var cached = logger.cache.remove(6),
    //         entry;

    //     cached.forEach(function (entry) {
    //         assert.ok(entry.namespace === logger.options.clientPrefix + logger.options.defaultNamespace);
    //         assert.ok(jQuery.type(entry.args) === "array");
    //         assert.ok(typeof entry.time === "string");
    //     });

    //     // log is different
    //     entry = cached[0];
    //     assert.ok(entry.level === 1);
    //     assert.ok(entry.args[0] === 0);

    //     ["debug", "info", "warn", "error", "metric"].forEach(function (level, i) {
    //         entry = cached[i + 1];
    //         assert.ok(entry.level === logger._parseLevel(level));
    //         assert.ok(entry.args[0] === i + 1);
    //     });
    // });

    // // ======================================================================== LoggingCache
    // QUnit.test("cache construction/initializiation defaults", function (assert) {
    //     // use empty to prevent tests stepping on one another due to persistence
    //     var cache = new metrics.LoggingCache({ key: "logs-test" }).empty();
    //     assert.equal(cache.maxSize, 5000);
    //     assert.equal(window.localStorage.getItem("logs-test"), "[]");
    // });

    // QUnit.test("cache construction/initializiation failure", function (assert) {
    //     ////TODO: doesn't work - readonly
    //     //window.localStorage = null;
    //     //console.debug( 'localStorage:', window.localStorage );
    //     var oldFn = metrics.LoggingCache.prototype._hasStorage;
    //     metrics.LoggingCache.prototype._hasStorage = function () {
    //         return false;
    //     };
    //     assert.throws(
    //         function () {
    //             return new metrics.LoggingCache({ key: "logs-test" });
    //         },
    //         /LoggingCache needs localStorage/,
    //         "lack of localStorage throws error"
    //     );
    //     metrics.LoggingCache.prototype._hasStorage = oldFn;

    //     assert.throws(
    //         function () {
    //             return new metrics.LoggingCache();
    //         },
    //         /LoggingCache needs key for localStorage/,
    //         "lack of key throws error"
    //     );
    // });

    // QUnit.test("cache construction/initializiation setting max cache size", function (assert) {
    //     var cache = new metrics.LoggingCache({
    //         key: "logs-test",
    //         maxSize: 5,
    //     }).empty();
    //     assert.equal(cache.maxSize, 5);
    // });

    // QUnit.test("cache plays well with no data", function (assert) {
    //     var cache = new metrics.LoggingCache({ key: "logs-test" }).empty();

    //     assert.equal(cache.length(), 0);
    //     var get = cache.get(10);
    //     assert.ok(jQuery.type(get) === "array" && get.length === 0);
    //     var remove = cache.remove(10);
    //     assert.ok(jQuery.type(remove) === "array" && remove.length === 0);
    //     assert.equal(cache.length(), 0);
    // });

    test("cache add properly adds and removes data", function () {
        const cache = new metrics.LoggingCache({
            key: "logs-test",
            maxSize: 5,
        }).empty();

        const entry1 = [{ one: 1 }, "two"];
        cache.add(entry1);

        expect(cache.length()).toBe(1);
        expect(JSON.stringify(cache.get(1)[0])).toBe(JSON.stringify(entry1));

        const entry2 = { blah: { one: 1 }, bler: ["three", { two: 2 }] };
        cache.add(entry2);
        expect(cache.length()).toBe(2);
        expect(cache.stringify(2)).toBe("[" + JSON.stringify(entry1) + "," + JSON.stringify(entry2) + "]");

        // FIFO
        var returned = cache.remove(1);
        assert.equal(cache.length(), 1);
        assert.ok(jQuery.type(returned) === "array" && returned.length === 1);
        var returned0 = returned[0];
        assert.ok(jQuery.type(returned0) === "array" && JSON.stringify(returned0) === JSON.stringify(entry1));
    });

    test("cache past max loses oldest", function () {
        const cache = new metrics.LoggingCache({
            key: "logs-test",
            maxSize: 5,
        }).empty();

        for (let i = 0; i < 10; i += 1) {
            cache.add({ index: i });
        }
        expect(cache.length()).toBe(5);
        const get = cache.get(5);
        expect(get[0].index === 5).toBeTruthy();
        expect(get[1].index === 6).toBeTruthy();
        expect(get[2].index === 7).toBeTruthy();
        expect(get[3].index === 8).toBeTruthy();
        expect(get[4].index === 9).toBeTruthy();
    });

    test("cache is properly persistent", function () {
        const cache1 = new metrics.LoggingCache({ key: "logs-test" }).empty();
        const entry = [{ one: 1 }, "two"];
        cache1.add(entry);
        expect(cache1.length()).toBe(1);

        const cache2 = new metrics.LoggingCache({ key: "logs-test" });
        expect(cache2.length()).toBe(1); // , "old key gets previously stored");
        expect(JSON.stringify(cache2.get(1)[0])).toBe(JSON.stringify(entry));

        const cache3 = new metrics.LoggingCache({ key: "logs-bler" });
        expect(cache3.length()).toBe(0); //, "new key causes new storage");
    });
});
