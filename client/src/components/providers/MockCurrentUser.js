const MockCurrentUser = (fakeUser) => ({
    render() {
        const slotFn = this.$slots.default;
        if (slotFn) {
            return slotFn({
                user: fakeUser,
            });
        }
        return null;
    },
});

export default MockCurrentUser;
