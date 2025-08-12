const MockUserHistories = (currentHistory = { id: "xyz" }, histories = [{ id: "abc" }], historiesLoading = false) => ({
    render() {
        return this.$slots.default({
            currentHistory: currentHistory,
            histories: histories,
            historiesLoading: historiesLoading,
            handlers: {},
        });
    },
});

export default MockUserHistories;
