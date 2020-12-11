export default {
    name: "development configs",
    debug: true,
    rxjsDebug: true,
    caching: {
        // adapter: "idb",
        adapter: "memory",
        revs_limit: 1,
        pageSize: 50,
    },
};
