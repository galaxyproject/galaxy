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
    // Compat RENDER_FUNCTION would make `$slots.default` an invoked vnode array instead of the slot function.
    compatConfig: { RENDER_FUNCTION: false },
    render() {
        const slotFn = this.$slots.default;
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
