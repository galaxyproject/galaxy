export default {
    props: {
        scope: { type: String, required: true },
        getKey: { type: Function, required: true },
    },
    data() {
        return {
            items: new Set(),
        };
    },
    computed: {
        slotProps() {
            return {
                items: this.items,
                has: this.has,
                toggle: this.toggle,
                reset: this.reset,
            };
        },
    },
    methods: {
        has(item) {
            const key = this.getKey(item);
            return this.items.has(key);
        },
        toggle(item, val) {
            const key = this.getKey(item);
            const newSet = new Set(this.items);
            val ? newSet.add(key) : newSet.delete(key);
            this.items = newSet;
        },
        reset() {
            this.items = new Set();
        },
    },
    watch: {
        scope(newKey, oldKey) {
            if (newKey !== oldKey) {
                this.reset();
            }
        },
    },
    render() {
        return this.$scopedSlots.default(this.slotProps);
    },
};
