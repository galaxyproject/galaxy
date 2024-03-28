import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import VueRouter from "vue-router";

import GenericElement from "./GenericElement";

jest.mock("components/History/model/queries");

const localVue = getLocalVue();
localVue.use(VueRouter);
const router = new VueRouter();

describe("GenericElement", () => {
    let wrapper;

    beforeEach(() => {
        wrapper = mount(GenericElement, {
            propsData: {
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
            localVue,
            router,
            pinia: createTestingPinia(),
        });
    });

    it("check basics", async () => {
        const contentItems = wrapper.findAll(".content-item");
        expect(contentItems.length).toBe(2);
        expect(contentItems.at(0).attributes("data-hid")).toBe("1");
        expect(contentItems.at(1).attributes("data-hid")).toBe("2");
        await contentItems.at(1).find(".cursor-pointer").trigger("click");
        const contentExpanded = wrapper.findAll(".content-item");
        expect(contentExpanded.length).toBe(4);
        expect(contentExpanded.at(2).attributes("data-hid")).toBe("3");
        expect(contentExpanded.at(3).attributes("data-hid")).toBe("4");
    });
});
