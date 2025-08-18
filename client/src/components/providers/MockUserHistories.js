const MockUserHistories = (currentHistory = { id: "xyz" }, histories = [{ id: "abc" }], historiesLoading = false) => ({
    render() {
        const slot = this.$slots.default;
        if (slot) {
            return slot({
                currentHistory: currentHistory,
                histories: histories,
                historiesLoading: historiesLoading,
                handlers: {},
            });
        }
        return null;
    },
});

export default MockUserHistories;
