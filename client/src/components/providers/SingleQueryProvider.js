import hash from "object-hash";

/**
 * Builds a provider that gets its result from a single promise-based query function and
 * caches the result of lookup for subsequent instantitations.
 *
 * @param   {Function}  lookup  async function that loads the result, paramters will be an object
 *                              whose properties are the attributes assigned to the provider component
 * @return  {VueComponentOptions} Vue component options definition
 */
export const SingleQueryProvider = (lookup) => {
    const promiseCache = new Map();
    const resultCache = new Map();

    return {
        data() {
            return {
                result: undefined,
            };
        },
        computed: {
            loading() {
                return this.result === undefined;
            },
            cacheKey() {
                hash(this.$attrs || {});
            },
        },
        mounted() {
            const cachedResult = resultCache.get(this.cacheKey);
            if (cachedResult) {
                this.result = cachedResult;
                return;
            }

            let lookupPromise = promiseCache.get(this.cacheKey);
            if (!lookupPromise) {
                lookupPromise = lookup(this.$attrs).catch((err) => {
                    this.$emit("error", err);
                });
                promiseCache.set(this.cacheKey, lookupPromise);
            }

            lookupPromise.then((result) => {
                resultCache.set(this.cacheKey, result);
                this.result = result;
            });
        },
        render() {
            return this.$scopedSlots.default({
                loading: this.loading,
                result: this.result,
            });
        },
    };
};
