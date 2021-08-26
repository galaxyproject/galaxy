const MockProvider = (fakeData) => ({
    render() {
        const resultLabel = fakeData.resultLabel || "result";
        return this.$scopedSlots.default({
            [resultLabel]: fakeData.result,
            loaded: true,
        });
    },
});

export default MockProvider;
