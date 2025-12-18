// Mock for portal-vue which is incompatible with Vue 3
// Used by bootstrap-vue internally for modals and tooltips

import { defineComponent, h, Teleport } from "vue";

// Create a simple Portal component that uses Vue 3's Teleport
export const Portal = defineComponent({
    name: "Portal",
    props: {
        to: {
            type: String,
            default: "body",
        },
        disabled: Boolean,
        slim: Boolean,
    },
    render() {
        const slot = this.$slots.default ? this.$slots.default() : [];
        if (this.disabled) {
            return slot;
        }
        return h(Teleport, { to: this.to }, slot);
    },
});

// PortalTarget is where portaled content appears
export const PortalTarget = defineComponent({
    name: "PortalTarget",
    props: {
        name: {
            type: String,
            required: true,
        },
        multiple: Boolean,
        tag: {
            type: String,
            default: "div",
        },
    },
    render() {
        return h(this.tag, { id: this.name }, this.$slots.default ? this.$slots.default() : []);
    },
});

// MountingPortal renders content in a target
export const MountingPortal = defineComponent({
    name: "MountingPortal",
    props: {
        mountTo: String,
        append: Boolean,
        bail: Boolean,
        disabled: Boolean,
        name: String,
        order: Number,
        slim: Boolean,
        targetSlim: Boolean,
        tag: {
            type: String,
            default: "div",
        },
        targetTag: {
            type: String,
            default: "div",
        },
    },
    render() {
        const slot = this.$slots.default ? this.$slots.default() : [];
        if (this.disabled) {
            return slot;
        }
        return h(Teleport, { to: this.mountTo || "body" }, slot);
    },
});

// Wormhole for portal communication (stubbed)
export const Wormhole = {
    open: () => {},
    close: () => {},
    transports: {},
    targets: {},
    sources: {},
};

// Plugin install function
const PortalVue = {
    install(app) {
        app.component("Portal", Portal);
        app.component("PortalTarget", PortalTarget);
        app.component("MountingPortal", MountingPortal);
    },
};

export default PortalVue;
