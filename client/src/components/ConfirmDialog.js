export default {
    methods: {
        async confirm(message, options = {}) {
            return this.$bvModal.msgBoxConfirm(message, {
                title: "请确认",
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
