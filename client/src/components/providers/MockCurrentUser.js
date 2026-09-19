const MockCurrentUser = (fakeUser) => ({
    render() {
        return this.$scopedSlots.default({
            user: fakeUser,
        });
    },
});

export default MockCurrentUser;
