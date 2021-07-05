export const SingleQueryProvider = (cfg = {}) => {
    const { resultName = "result", lookup } = cfg;

    let cached_result;

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
        },
        async created() {
            if (undefined === cached_result) {
                cached_result = await lookup();
            }
            this.result = cached_result;
        },
        render() {
            return this.$scopedSlots.default({
                loading: this.loading,
                [resultName]: this.result,
            });
        },
    };
};
