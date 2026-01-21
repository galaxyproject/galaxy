const MockCurrentHistory = (currentHistory = { id: "xyz" }) => ({
    render() {
        // Use $scopedSlots for Vue 3 compat mode
        const slotFn = this.$scopedSlots?.default || this.$slots?.default;
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
