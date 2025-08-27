const MockProvider = (fakeData) => ({
    render() {
        const resultLabel = fakeData.resultLabel || "result";
        const slot = this.$slots.default;
        if (slot) {
            return slot({
                [resultLabel]: fakeData.result,
                loaded: true,
            });
        }
        return null;
    },
});

export default MockProvider;
