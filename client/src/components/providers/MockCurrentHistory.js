const MockCurrentHistory = (currentHistory = { id: "xyz" }) => ({
    render() {
        return (
            this.$slots.default &&
            this.$slots.default({
                currentHistory: currentHistory,
                currentHistoryId: currentHistory.id,
            })
        );
    },
});

export default MockCurrentHistory;
