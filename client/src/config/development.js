export default {
    name: "development",
    debug: true,
    rxjsDebug: true,
    caching: {
        adapter: "idb",
        revs_limit: 1,
        pageSize: 50,
    },
    /* global __buildTimestamp__ */
    buildTimestamp: __buildTimestamp__,
};
