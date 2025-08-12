const MockCurrentUser = (fakeUser) => ({
    render() {
        return this.$slots.default({
            user: fakeUser,
        });
    },
});

export default MockCurrentUser;
