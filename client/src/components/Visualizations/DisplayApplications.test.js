import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import DisplayApplications from "./DisplayApplications";

describe("DisplayApplications", () => {
    let wrapper;

    beforeEach(() => {
        const globalConfig = getLocalVue();
        
        // Create a Vue 3 compatible mock provider
        const mockData = {
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
        };
        
        wrapper = mount(DisplayApplications, {
            props: {
                datasetId: "dataset-id",
            },
            global: {
                ...globalConfig.global,
                stubs: {
                    DatasetProvider: {
                        template: '<div><slot :result="result" :loaded="loaded" /></div>',
                        data() {
                            return {
                                result: mockData,
                                loaded: true,
                            };
                        },
                    },
                },
            },
        });
    });

    it("check props", async () => {
        const labels = wrapper.findAll(".font-weight-bold");
        for (let i = 0; i < 2; i++) {
            expect(labels[i].text()).toBe(`app-${i + 1}`);
        }
        const links = wrapper.findAll("a");
        for (let i = 0; i < 3; i++) {
            expect(links[i].attributes("href")).toBe(`link-href-${i + 1}`);
            expect(links[i].attributes("target")).toBe(`link-target-${i + 1}`);
            expect(links[i].text()).toBe(`link-text-${i + 1}`);
        }
    });
});
