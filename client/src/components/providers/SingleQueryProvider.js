import hash from "object-hash";
import { LastQueue } from "utils/lastQueue";
import { computed, onMounted, onUnmounted, ref } from "vue";

/**
 * Composable for converting attributes from kebab-case to camelCase
 */
function useAttributes(attrs) {
    const toCamelCase = (attributes) => {
        const result = {};
        for (const key in attributes) {
            const newKey = key.replace(/-./g, (x) => x[1].toUpperCase());
            result[newKey] = attributes[key];
        }
        return result;
    };

    const attributes = computed(() => toCamelCase(attrs));

    return { attributes, toCamelCase };
}

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
        emits: ["update:result", "error"],
        setup(props, { slots, emit, attrs }) {
            const result = ref(null);
            const error = ref(null);
            const timeoutId = ref(null);
            const queue = new LastQueue(props.autoTime);

            const { attributes } = useAttributes(attrs);

            const loading = computed(() => result.value === null);
            const cacheKey = computed(() => hash(attrs || {}));

            function doQuery() {
                let lookupPromise;
                if (props.useCache) {
                    lookupPromise = promiseCache.get(cacheKey.value);
                    if (!lookupPromise) {
                        lookupPromise = lookup(attrs);
                        promiseCache.set(cacheKey.value, lookupPromise);
                    }
                } else {
                    lookupPromise = queue.enqueue(lookup, attributes.value);
                }
                lookupPromise.then(
                    (res) => {
                        result.value = res;
                        emit("update:result", res);
                        error.value = null;
                        if (props.autoRefresh && !stopRefresh(res)) {
                            timeoutId.value = setTimeout(() => {
                                doQuery();
                            }, props.autoTime);
                        }
                    },
                    (err) => {
                        result.value = {};
                        error.value = err;
                        emit("error", err);
                        console.debug("Failed to fulfill promise.", err);
                    },
                );
            }

            onMounted(() => {
                doQuery();
            });

            onUnmounted(() => {
                if (timeoutId.value) {
                    clearTimeout(timeoutId.value);
                }
            });

            return () => {
                if (!slots.default) {
                    return null;
                }
                return slots.default({
                    loading: loading.value,
                    result: result.value,
                    error: error.value,
                });
            };
        },
    };
};
