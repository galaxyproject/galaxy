export default {
    methods: {
        async confirm(message, options = {}) {
            // To allow for HTML content in the message, we need to convert it to a VNode.
            // https://bootstrap-vue.org/docs/components/modal#message-box-notes
            if (options.html) {
                message = this.htmlToVNode(message);
            }

            return this.$bvModal.msgBoxConfirm(message, {
                title: "Please Confirm",
                titleClass: "h-md",
                hideHeaderClose: false,
                ...options,
            });
        },
        htmlToVNode(html) {
            return [this.$createElement("div", { domProps: { innerHTML: html } })];
        },
    },
    render() {
        return {};
    },
};
