const MockUserHistories = (currentHistory = { id: "xyz" }, histories = [{ id: "abc" }], historiesLoading = false) => ({
    render() {
        // Use $scopedSlots for Vue 3 compat mode
        const slotFn = this.$scopedSlots?.default || this.$slots?.default;
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
