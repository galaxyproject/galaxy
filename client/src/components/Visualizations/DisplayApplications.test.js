import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

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
    display_types: [
        {
            label: "type-1",
            links: [
                {
                    href: "http://example.com/type-1-a",
                    target: "_blank",
                    text: "type-text-1a",
                },
                {
                    href: "http://example.com/type-1-b",
                    target: "_blank",
                    text: "type-text-1b",
                },
            ],
        },
        {
            label: "type-2",
            links: [
                {
                    href: "http://example.com/type-2-a",
                    target: "_blank",
                    text: "type-text-2a",
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
        expect(labels.at(0).text()).toBe("app-1");
        expect(labels.at(1).text()).toBe("app-2");
        expect(labels.at(2).text()).toBe("type-1");
        expect(labels.at(3).text()).toBe("type-2");

        const links = wrapper.findAll("a");
        expect(links.at(0).attributes("href")).toBe(getUrl(0));
        expect(links.at(0).text()).toBe("link-text-1");

        expect(links.at(1).attributes("href")).toBe(getUrl(1));
        expect(links.at(1).text()).toBe("link-text-2");

        expect(links.at(2).attributes("href")).toBe(getUrl(2));
        expect(links.at(2).text()).toBe("link-text-3");

        expect(links.at(3).attributes("href")).toBe("http://example.com/type-1-a");
        expect(links.at(3).text()).toBe("type-text-1a");

        expect(links.at(4).attributes("href")).toBe("http://example.com/type-1-b");
        expect(links.at(4).text()).toBe("type-text-1b");

        expect(links.at(5).attributes("href")).toBe("http://example.com/type-2-a");
        expect(links.at(5).text()).toBe("type-text-2a");
    });
});
