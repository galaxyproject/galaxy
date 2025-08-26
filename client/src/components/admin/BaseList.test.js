import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import BaseList from "./BaseList";


describe("Categories", () => {
    const getter = async () => {
        return {
            data: [
                {
                    col_0: "col_0_0",
                    col_1: "col_0_1",
                },
                {
                    col_0: "col_0_2",
                    col_1: "col_0_3",
                },
            ],
        };
    };
    const setter = async () => {
        return {};
    };
    test("test categories loading", async () => {
        const globalConfig = getLocalVue();
        const wrapper = mount(BaseList, {
            props: {
                icon: "fa fa-caret-down",
                tooltip: "tooltip",
                plural: "plural",
                success: "success",
                fields: ["execute", "col_0", "col_1"],
                getter: getter,
                setter: setter,
            },
            global: globalConfig.global,
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.find(".card-header").text()).toContain("There are 2");
        const th = wrapper.findAll("th");
        expect(th.length).toBe(3);
        expect(th[0].text()).toBe("Execute");
        expect(th[1].text()).toBe("Col 0");
        expect(th[2].text()).toBe("Col 1");
    });
});
