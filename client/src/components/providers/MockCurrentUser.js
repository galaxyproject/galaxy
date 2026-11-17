const MockCurrentUser = (fakeUser) => ({
    // Compat RENDER_FUNCTION would make `$slots.default` an invoked vnode array instead of the slot function.
    compatConfig: { RENDER_FUNCTION: false },
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
