const MockCurrentUser = (fakeUser) => ({
    render() {
        const slot = this.$slots.default;
        if (slot) {
            return slot({
                user: fakeUser,
            });
        }
        return null;
    },
});

export default MockCurrentUser;
