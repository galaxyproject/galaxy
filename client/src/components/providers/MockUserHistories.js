const MockUserHistories = (currentHistory = { id: "xyz" }, histories = [{ id: "abc" }], historiesLoading = false) => ({
    render() {
        const slotFn = this.$slots.default;
        if (slotFn) {
            return slotFn({
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
