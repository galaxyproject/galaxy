import { mount } from "@vue/test-utils";
import BaseList from "./BaseList";
import Vue from "vue";

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
    it("test categories loading", async () => {
        const wrapper = mount(BaseList, {
            propsData: {
                icon: "fa fa-caret-down",
                tooltip: "tooltip",
                plural: "plural",
                success: "success",
                fields: ["execute", "col_0", "col_1"],
                getter: getter,
                setter: setter,
            },
        });
        await Vue.nextTick();
        expect(wrapper.find(".card-header").text()).contains("There are 2");
        const th = wrapper.findAll("th");
        expect(th.length).to.equal(3);
        expect(th.at(0).text()).to.equal("Execute");
        expect(th.at(1).text()).to.equal("Col 0");
        expect(th.at(2).text()).to.equal("Col 1");
    });
});
