import { mount } from "@vue/test-utils";
import { createPinia, defineStore, setActivePinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";

import ConfigureHeader from "./ConfigureHeader.vue";
import ConfigureSelector from "./ConfigureSelector.vue";
import ConfigureVitessce from "./ConfigureVitessce.vue";

const localVue = getLocalVue();

let mockedStore;

jest.mock("@/stores/historyStore", () => {
    return {
        useHistoryStore: () => mockedStore,
    };
});

beforeEach(() => {
    setActivePinia(createPinia());
    mockedStore = defineStore("history", {
        state: () => ({
            currentHistoryId: "history123",
        }),
    })();
});

function mountComponent(content = {}) {
    return mount(ConfigureVitessce, {
        localVue,
        propsData: {
            name: "vitessce-view",
            content: JSON.stringify(content),
        },
        stubs: {
            ConfigureSelector: true,
            ConfigureHeader: true,
        },
    });
}

describe("ConfigureVitessce.vue", () => {
    it("renders error alert on invalid content", () => {
        const wrapper = mount(ConfigureVitessce, {
            localVue,
            propsData: {
                name: "vitessce-view",
                content: "{invalid-json",
            },
            stubs: {
                ConfigureSelector: true,
                ConfigureHeader: true,
            },
        });
        expect(wrapper.text()).toContain("Failed to parse:");
        expect(wrapper.findComponent({ name: "BAlert" }).exists()).toBe(true);
    });

    it("shows warning alert if no URL-like fields are found", () => {
        const wrapper = mountComponent({});
        expect(wrapper.text()).toContain("No URL-like fields found.");
        expect(wrapper.findComponent({ name: "BAlert" }).exists()).toBe(true);
    });

    it("renders ConfigureHeader and ConfigureSelector for each URL field", () => {
        const wrapper = mountComponent({
            datasets: [
                {
                    name: "Dataset 1",
                    uid: "ds1",
                    files: [
                        {
                            fileType: "obs",
                            url: "https://example.com/obs",
                            options: { obsType: "cell", obsIndex: "cell_id" },
                        },
                        {
                            fileType: "var",
                            url: "https://example.com/var",
                            options: { obsType: "gene" },
                        },
                    ],
                },
                {
                    name: "Dataset 2",
                    uid: "ds2",
                    files: [
                        {
                            fileType: "spatial",
                            url: "https://example.com/spatial",
                        },
                    ],
                },
            ],
        });
        expect(wrapper.findComponent(ConfigureHeader).exists()).toBe(true);
        expect(wrapper.findAllComponents(ConfigureSelector)).toHaveLength(3);
    });

    it("emits cancel when ConfigureHeader triggers it", async () => {
        const wrapper = mountComponent({});
        wrapper.findComponent(ConfigureHeader).vm.$emit("cancel");
        expect(wrapper.emitted("cancel")).toBeTruthy();
    });

    it("emits change with updated JSON when OK is clicked", async () => {
        const wrapper = mountComponent({
            datasets: [
                {
                    name: "Dataset 1",
                    uid: "ds1",
                    files: [{ fileType: "obs", url: "https://example.com/obs" }],
                },
            ],
        });
        wrapper.findComponent(ConfigureHeader).vm.$emit("ok");
        expect(wrapper.emitted("change")).toBeTruthy();
        const emittedJson = wrapper.emitted("change")[0][0];
        expect(typeof emittedJson).toBe("string");
        expect(JSON.parse(emittedJson)).toMatchObject({
            datasets: [{ name: "Dataset 1", uid: "ds1" }],
        });
    });
});
