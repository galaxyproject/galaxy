const MockUserHistories = (currentHistory = { id: "xyz" }, histories = [{ id: "abc" }], historiesLoading = false) => ({
    // Compat RENDER_FUNCTION would make `$slots.default` an invoked vnode array instead of the slot function.
    compatConfig: { RENDER_FUNCTION: false },
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
