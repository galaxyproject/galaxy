export default {
    name: "production",
    debug: false,
    rxjsDebug: false,
    caching: {
        adapter: "idb",
        revs_limit: 1,
        pageSize: 60,
    },
    /* global __buildTimestamp__ */
    buildTimestamp: __buildTimestamp__,
};
