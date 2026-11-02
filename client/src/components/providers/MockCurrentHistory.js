const MockCurrentHistory = (currentHistory = { id: "xyz" }) => ({
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
