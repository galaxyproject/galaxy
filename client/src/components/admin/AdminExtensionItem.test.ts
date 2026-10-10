import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, h } from "vue";

import { type AdminExtension, useAdminExtensionsStore } from "@/stores/adminExtensionsStore";

import AdminExtensionItem from "./AdminExtensionItem.vue";

// FormGeneric fetches its inputs from the server on mount; the form contract is
// covered by the integration tests, so here it is replaced by a marker element.
vi.mock("@/components/Form/FormGeneric.vue", () => ({
    default: defineComponent({
        props: { id: String, url: String },
        setup(props) {
            return () => h("form", { id: props.id, "data-url": props.url });
        },
    }),
}));

const localVue = getLocalVue(true);

const EXTENSIONS: AdminExtension[] = [
    {
        id: "anvil",
        section: "AnVIL",
        items: [
            { id: "monitor", type: "link", title: "Cluster Monitor", url: "/monitor", target: "iframe" },
            {
                id: "batch",
                type: "form",
                title: "GCP Batch",
                description: null,
                inputs: [
                    {
                        name: "ttl",
                        key: "gcp_batch.pool_ttl_seconds",
                        type: "integer",
                        label: "Idle seconds",
                        help: null,
                        default: 300,
                        options: null,
                        min: 0,
                        max: null,
                    },
                ],
            },
        ],
    },
];

interface StoreState {
    extensions?: AdminExtension[];
    loaded?: boolean;
    errorMessage?: string | null;
}

function mountItem(state: StoreState, extensionId = "anvil", itemId = "monitor") {
    const pinia = createTestingPinia({ stubActions: true, createSpy: vi.fn });
    const store = useAdminExtensionsStore(pinia);
    store.extensions = state.extensions ?? [];
    store.loaded = state.loaded ?? false;
    store.errorMessage = state.errorMessage ?? null;
    return mount(AdminExtensionItem as object, {
        global: localVue,
        pinia,
        props: { extensionId, itemId },
        stubs: { CenterFrame: { props: ["id", "src"], template: "<iframe :id='id' :src='src' />" } },
    });
}

describe("AdminExtensionItem", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("shows a loading message until extensions are loaded", () => {
        const wrapper = mountItem({ loaded: false });
        expect(wrapper.text()).toContain("Loading admin extension");
        expect(wrapper.find("iframe").exists()).toBe(false);
    });

    it("frames the item url once loaded", () => {
        const wrapper = mountItem({ extensions: EXTENSIONS, loaded: true });
        const frame = wrapper.find("iframe");
        expect(frame.exists()).toBe(true);
        expect(frame.attributes("src")).toBe("/monitor");
        expect(frame.attributes("id")).toBe("admin-extension-anvil-monitor");
    });

    it("renders a form item through the generic form bound to its form endpoint", () => {
        const wrapper = mountItem({ extensions: EXTENSIONS, loaded: true }, "anvil", "batch");
        const form = wrapper.find("form");
        expect(form.exists()).toBe(true);
        expect(form.attributes("data-url")).toBe("/api/admin/extensions/anvil/items/batch/form");
        expect(form.attributes("id")).toBe("admin-extension-anvil-batch");
        expect(wrapper.find("iframe").exists()).toBe(false);
    });

    it("shows a warning when the item does not exist", () => {
        const wrapper = mountItem({ extensions: EXTENSIONS, loaded: true }, "anvil", "missing");
        expect(wrapper.find(".alert-warning").text()).toContain('No admin extension item "missing"');
        expect(wrapper.find("iframe").exists()).toBe(false);
    });

    it("shows the error when loading failed", () => {
        const wrapper = mountItem({ loaded: false, errorMessage: "Request failed." });
        expect(wrapper.find(".alert-danger").text()).toContain("Request failed.");
        expect(wrapper.find("iframe").exists()).toBe(false);
    });
});
