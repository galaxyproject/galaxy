const MockCurrentHistory = (currentHistory = { id: "xyz" }) => ({
    // Compat RENDER_FUNCTION would make `$slots.default` an invoked vnode array instead of the slot function.
    compatConfig: { RENDER_FUNCTION: false },
    render() {
        const slotFn = this.$slots.default;
        if (slotFn) {
            return slotFn({
                currentHistory: currentHistory,
                currentHistoryId: currentHistory.id,
            });
        }
        return null;
    },
});

export default MockCurrentHistory;
