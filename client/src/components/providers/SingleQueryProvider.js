import hash from "object-hash";
import { LastQueue } from "utils/promise-queue";

/**
 * Builds a provider that gets its result from a single promise-based query function and
 * caches the result of lookup for subsequent instantiations.
 *
 * @param   {Function}  lookup  async function that loads the result, parameters will be an object
 *                              whose properties are the attributes assigned to the provider component
 * @return  {VueComponentOptions} Vue component options definition
 */
export const SingleQueryProvider = (lookup) => {
    const promiseCache = new Map();
    return {
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
                default: 500,
            },
        },
        data() {
            return {
                result: null,
                error: null,
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
            if (this.autoRefresh) {
                this.interval = setInterval(() => {
                    this.doQuery();
                }, this.autoTime);
            }
        },
        destroyed() {
            if (this.interval) {
                clearInterval(this.interval);
            }
        },
        render() {
            return this.$scopedSlots.default({
                loading: this.loading,
                result: this.result,
                error: this.error,
            });
        },
        methods: {
            doQuery() {
                let lookupPromise;
                if (this.useCache) {
                    lookupPromise = promiseCache.get(this.cacheKey);
                    if (!lookupPromise) {
                        lookupPromise = lookup(this.$attrs);
                        promiseCache.set(this.cacheKey, lookupPromise);
                    }
                } else {
                    lookupPromise = this.queue.enqueue(lookup, this.$attrs);
                }
                lookupPromise.then(
                    (result) => {
                        this.result = result;
                        this.error = null;
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
