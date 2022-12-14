import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import DisplayApplications from "./DisplayApplications";
import MockProvider from "components/providers/MockProvider";

const localVue = getLocalVue();

describe("DisplayApplications", () => {
    let wrapper;

    beforeEach(() => {
        wrapper = mount(DisplayApplications, {
            propsData: {
                datasetId: "dataset-id",
            },
            stubs: {
                DatasetProvider: MockProvider({
                    result: {
                        display_apps: [
                            {
                                label: "app-1",
                                links: [
                                    {
                                        href: "link-href-1",
                                        text: "link-text-1",
                                        target: "link-target-1",
                                    },
                                ],
                            },
                            {
                                label: "app-2",
                                links: [
                                    {
                                        href: "link-href-2",
                                        text: "link-text-2",
                                        target: "link-target-2",
                                    },
                                    {
                                        href: "link-href-3",
                                        text: "link-text-3",
                                        target: "link-target-3",
                                    },
                                ],
                            },
                        ],
                    },
                }),
            },
            localVue,
        });
    });

    it("check props", async () => {
        const labels = wrapper.findAll(".font-weight-bold");
        for (let i = 0; i < 2; i++) {
            expect(labels.at(i).text()).toBe(`app-${i + 1}`);
        }
        const links = wrapper.findAll("a");
        for (let i = 0; i < 3; i++) {
            expect(links.at(i).attributes("href")).toBe(`link-href-${i + 1}`);
            expect(links.at(i).attributes("target")).toBe(`link-target-${i + 1}`);
            expect(links.at(i).text()).toBe(`link-text-${i + 1}`);
        }
    });
});
