export default {
    methods: {
        async confirm(message, options = {}) {
            return this.$bvModal.msgBoxConfirm(message, {
                title: "Please Confirm",
                titleClass: "h-md",
                hideHeaderClose: false,
                ...options,
            });
        },
    },
    render() {
        return {};
    },
};
