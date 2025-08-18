import { loadSet, saveSet } from "utils/setCache";
import { computed, onBeforeMount,ref, watch } from "vue";

export default {
    props: {
        scopeKey: { type: String, required: true },
        getItemKey: { type: Function, required: true },
    },
    setup(props, { slots }) {
        const items = ref(new Set());
        const key = "expanded-history-items";

        const expandedCount = computed(() => items.value.size);

        function isExpanded(item) {
            const itemKey = props.getItemKey(item);
            return items.value.has(itemKey);
        }

        function setExpanded(item, val) {
            const itemKey = props.getItemKey(item);
            const newSet = new Set(items.value);
            val ? newSet.add(itemKey) : newSet.delete(itemKey);
            items.value = newSet;
        }

        function reset() {
            items.value = new Set();
        }

        watch(
            () => props.scopeKey,
            (newKey, oldKey) => {
                if (newKey !== oldKey) {
                    reset();
                }
            }
        );

        watch(items, (newSet) => {
            saveSet(key, newSet);
        });

        onBeforeMount(() => {
            const cachedSet = loadSet(key);
            if (cachedSet) {
                items.value = cachedSet;
            }
        });

        return () => {
            if (!slots.default) {
                return null;
            }
            return slots.default({
                isExpanded: isExpanded,
                setExpanded: setExpanded,
                collapseAll: reset,
                expandedCount: expandedCount.value,
            });
        };
    },
};
