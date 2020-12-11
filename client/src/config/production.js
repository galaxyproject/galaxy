export default {
    name: "production configs",
    debug: false,
    caching: {
        adapter: "idb",
        revs_limit: 1,
        pageSize: 60,
    },
};
