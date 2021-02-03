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
    },
    render() {
        return this.$scopedSlots.default({
            isExpanded: this.isExpanded,
            setExpanded: this.setExpanded,
        });
    },
};
