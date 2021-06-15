/**
 * Indices are required by pouchdb to use the pouuchdb.find functionality. These
 * are the indices we keep on the main history content database
 */

export const contentIndices = [
    {
        index: {
            fields: [{ cached_at: "desc" }],
        },
        name: "by cache time",
        ddoc: "idx-content-history-cached_at",
    },
];

/**
 * ...and the collection contents
 */

export const dscIndices = [
    {
        index: {
            fields: [{ cached_at: "desc" }],
        },
        name: "by cache time",
        ddoc: "idx-dsc-contents-cached_at",
    },
];
