/**
 * Makes lists
 */
export default {
    props: {
        tag: { type: String, required: false, default: "ul" },
        childTag: { type: String, required: false, default: "li" },
    },
    render(h) {
        const renderChild = (vnode) => h(this.childTag, [vnode]);
        const slotNodes = this.$slots.default || [];
        const menu = slotNodes.map(renderChild);
        return h(this.tag, menu);
    },
};
