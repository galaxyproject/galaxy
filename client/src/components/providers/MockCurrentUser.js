const MockCurrentUser = (fakeUser) => ({
    render() {
        // Use $scopedSlots for Vue 3 compat mode
        const slotFn = this.$scopedSlots?.default || this.$slots?.default;
        if (slotFn) {
            return slotFn({
                user: fakeUser,
            });
        }
        return null;
    },
});

export default MockCurrentUser;
