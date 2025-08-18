const MockCurrentHistory = (currentHistory = { id: "xyz" }) => ({
    render() {
        const slot = this.$slots.default;
        if (slot) {
            return slot({
                currentHistory: currentHistory,
                currentHistoryId: currentHistory.id,
            });
        }
        return null;
    },
});

export default MockCurrentHistory;
