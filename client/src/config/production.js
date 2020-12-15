export default {
    name: "production configs",
    debug: false,
    rxjsDebug: false,
    caching: {
        adapter: "idb",
        revs_limit: 1,
        pageSize: 60,
    },
};
