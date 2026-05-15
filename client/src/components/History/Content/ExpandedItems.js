import { loadSet, saveSet } from "@/utils/setCache";

export default {
    props: {
        scopeKey: { type: String, required: true },
        getItemKey: { type: Function, required: true },
    },
    data() {
        return {
            items: new Set(),
        };
    },
    computed: {
        expandedCount() {
            return this.items.size;
        },
    },
    methods: {
        isExpanded(item) {
            const key = this.getItemKey(item);
            return this.items.has(key);
        },
        setExpanded(item, val) {
            const key = this.getItemKey(item);
            const newSet = new Set(this.items);
            val ? newSet.add(key) : newSet.delete(key);
            this.items = newSet;
        },
        reset() {
            this.items = new Set();
        },
    },
    watch: {
        scopeKey(newKey, oldKey) {
            if (newKey !== oldKey) {
                this.reset();
            }
        },
        items(newSet) {
            saveSet(this.key, newSet);
        },
    },
    created() {
        this.key = "expanded-history-items";
        const cachedSet = loadSet(this.key);
        if (cachedSet) {
            this.items = cachedSet;
        }
    },
    render() {
        // Use $scopedSlots for Vue 3 compat mode
        const slotFn = this.$scopedSlots?.default || this.$slots?.default;
        if (slotFn) {
            return slotFn({
                isExpanded: this.isExpanded,
                setExpanded: this.setExpanded,
                collapseAll: this.reset,
                expandedCount: this.expandedCount,
            });
        }
        return null;
    },
};
