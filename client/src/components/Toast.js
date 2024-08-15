export default {
    methods: {
        showToast(message, title, variant, href) {
            this.$bvToast.toast(message, {
                variant,
                title,
                href,
                toaster: "b-toaster-bottom-right",
                appendToast: true,
                solid: true,
            });
        },
    },
    render() {
        return {};
    },
};
