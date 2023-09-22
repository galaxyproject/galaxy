const MockCurrentHistory = (currentHistory = { id: "xyz" }) => ({
    render() {
        return this.$scopedSlots.default({
            currentHistory: currentHistory,
            currentHistoryId: currentHistory.id,
        });
    },
});

export default MockCurrentHistory;
