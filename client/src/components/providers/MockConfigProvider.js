const MockConfigProvider = (fakeConfig) => ({
    render() {
        return this.$scopedSlots.default({
            config: fakeConfig,
        });
    },
});

export default MockConfigProvider;
