export default {
    methods: {
        showToast(message, title, variant) {
            this.$bvToast.toast(message, {
                variant,
                title,
                toaster: "b-toaster-bottom-right",
                append: true,
                solid: true,
            });
        },
    },
    render() {
        return {};
    },
};
