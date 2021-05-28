export default (lookup) => ({
    data() {
        return {
            result: [],
        };
    },
    created() {
        this.load();
    },
    methods: {
        async load() {
            this.result = await lookup();
        },
    },
    render() {
        return this.$scopedSlots.default({
            result: this.result,
            load: this.load,
        });
    },
});
