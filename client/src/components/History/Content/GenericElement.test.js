import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import { getLocalVue, injectTestRouter, suppressLucideVue2Deprecation } from "tests/jest/helpers";

import { setupSelectableMock } from "@/components/ObjectStore/mockServices";

import GenericElement from "./GenericElement";

jest.mock("components/History/model/queries");

setupSelectableMock();

const globalConfig = getLocalVue();
const router = injectTestRouter();

describe("GenericElement", () => {
    let wrapper;

    beforeEach(() => {
        suppressLucideVue2Deprecation();

        wrapper = mount(GenericElement, {
            props: {
                dsc: {
                    elements: [
                        {
                            element_index: 0,
                            element_identifier: "element-1",
                            element_type: "hda",
                            object: {
                                id: "item-1",
                            },
                        },
                        {
                            element_index: 1,
                            element_identifier: "element-2",
                            element_type: "hdca",
                            object: {
                                id: "item-2",
                                collection_type: "list",
                                element_count: 1,
                                elements_datatypes: ["txt"],
                                elements: [
                                    {
                                        element_index: 2,
                                        element_identifier: "element-3",
                                        element_type: "hda",
                                        object: {
                                            id: "item_3",
                                        },
                                    },
                                    {
                                        element_index: 3,
                                        element_identifier: "element-4",
                                        element_type: "hda",
                                        object: {
                                            id: "item_4",
                                        },
                                    },
                                ],
                            },
                        },
                    ],
                },
            },
            ...globalConfig,
            global: {
                ...globalConfig.global,
                plugins: [...globalConfig.global.plugins, createTestingPinia(), router],
            },
        });
    });

    it("check basics", async () => {
        const contentItems = wrapper.findAll(".content-item");
        expect(contentItems.length).toBe(2);
        expect(contentItems[0].attributes("data-hid")).toBe("1");
        expect(contentItems[1].attributes("data-hid")).toBe("2");
        await contentItems[1].find(".cursor-pointer").trigger("click");
        const contentExpanded = wrapper.findAll(".content-item");
        expect(contentExpanded.length).toBe(4);
        expect(contentExpanded[2].attributes("data-hid")).toBe("3");
        expect(contentExpanded[3].attributes("data-hid")).toBe("4");
    });
});
