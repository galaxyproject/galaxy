import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import MockProvider from "@/components/providers/MockProvider";

import DisplayApplications from "./DisplayApplications.vue";

const localVue = getLocalVue();

const raw = {
    display_apps: [
        {
            label: "app-1",
            links: [
                {
                    app_name: "link-app-1",
                    link_name: "link-name-1",
                    text: "link-text-1",
                },
            ],
        },
        {
            label: "app-2",
            links: [
                {
                    app_name: "link-app-2",
                    link_name: "link-name-2",
                    text: "link-text-2",
                },
                {
                    app_name: "link-app-3",
                    link_name: "link-name-3",
                    text: "link-text-3",
                },
            ],
        },
    ],
};

jest.mock("../providers/DatasetProvider", () => ({
    render() {
        return this.$scopedSlots.default({
            loading: false,
            result: raw,
        });
    },
}));

function mountTarget() {
    return mount(DisplayApplications, {
        propsData: {
            datasetId: "dataset-id",
        },
        stubs: {
            RouterLink: {
                props: ["to"],
                render(h) {
                    return h("a", { attrs: { href: this.to } }, this.$slots.default);
                },
            },
        },
        localVue,
    });
}

function getUrl(i) {
    return `/display_applications/dataset-id/link-app-${i + 1}/link-name-${i + 1}`;
}

describe("DisplayApplications", () => {
    it("check props", async () => {
        const wrapper = mountTarget();
        const labels = wrapper.findAll(".font-weight-bold");
        for (let i = 0; i < 2; i++) {
            expect(labels.at(i).text()).toBe(`app-${i + 1}`);
        }
        const links = wrapper.findAll("a");
        for (let i = 0; i < 3; i++) {
            expect(links.at(i).attributes("href")).toBe(getUrl(i));
            expect(links.at(i).text()).toBe(`link-text-${i + 1}`);
        }
    });
});
