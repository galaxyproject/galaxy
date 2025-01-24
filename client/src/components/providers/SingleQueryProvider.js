import hash from "object-hash";
import { LastQueue } from "utils/lastQueue";

import { HasAttributesMixin } from "./utils";

/**
 * Builds a provider that gets its result from a single promise-based query function and
 * caches the result of lookup for subsequent instantiations.
 *
 * @param   {Function}  lookup  async function that loads the result, parameters will be an object
 *                              whose properties are the attributes assigned to the provider component
 * @param   {Function}  stopRefresh function that will be called with result of lookup.
 *                                  If function returns true refresh will be stopped.
 * @return  {VueComponentOptions} Vue component options definition
 */
export const SingleQueryProvider = (lookup, stopRefresh = (result) => false) => {
    const promiseCache = new Map();
    return {
        mixins: [HasAttributesMixin],
        props: {
            useCache: {
                type: Boolean,
                default: false,
            },
            autoRefresh: {
                type: Boolean,
                default: false,
            },
            autoTime: {
                type: Number,
                default: 3000,
            },
        },
        data() {
            return {
                result: null,
                error: null,
                timeoutId: null,
            };
        },
        created() {
            this.queue = new LastQueue(this.autoTime);
        },
        computed: {
            loading() {
                return this.result === null;
            },
            cacheKey() {
                return hash(this.$attrs || {});
            },
        },
        mounted() {
            this.doQuery();
        },
        destroyed() {
            if (this.timeoutId) {
                clearTimeout(this.timeoutId);
            }
        },
        render() {
            return (
                this.$scopedSlots.default &&
                this.$scopedSlots.default({
                    loading: this.loading,
                    result: this.result,
                    error: this.error,
                })
            );
        },
        methods: {
            update(attributes) {
                for (var attrname in attributes) {
                    this.attributes[attrname] = attributes[attrname];
                }
                this.doQuery();
            },
            doQuery() {
                let lookupPromise;
                if (this.useCache) {
                    lookupPromise = promiseCache.get(this.cacheKey);
                    if (!lookupPromise) {
                        lookupPromise = lookup(this.$attrs);
                        promiseCache.set(this.cacheKey, lookupPromise);
                    }
                } else {
                    lookupPromise = this.queue.enqueue(lookup, this.attributes);
                }
                lookupPromise.then(
                    (result) => {
                        this.result = result;
                        this.$emit("update:result", result);
                        this.error = null;
                        if (this.autoRefresh && !stopRefresh(result)) {
                            this.timeoutId = setTimeout(() => {
                                this.doQuery();
                            }, this.autoTime);
                        }
                    },
                    (err) => {
                        this.result = {};
                        this.error = err;
                        this.$emit("error", err);
                        console.debug("Failed to fulfill promise.", err);
                    }
                );
            },
        },
    };
};
