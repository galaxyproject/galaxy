import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import FormSelect from "./FormSelect";
import Multiselect from "vue-multiselect";

const localVue = getLocalVue();

describe("FormSelect", () => {
    it("Sets default currentValue as first option when not told otherwise", async () => {
        const wrapper = mount(FormSelect, {
            propsData: {
                value: "",
                defaultValue: "",
                options: [
                    ["test1", "T", false],
                    ["test2", "2", false],
                ],
            },
            localVue,
        });
        expect(wrapper.vm.currentValue).toStrictEqual({ label: "test1", value: "T", default: false });
    });
    it("Sets default currentValue to object with 'default: true' when default not provided from defaultValue", async () => {
        const wrapper = mount(FormSelect, {
            propsData: {
                value: "",
                defaultValue: "",
                options: [
                    ["test1", "T", false],
                    ["test2", "2", true],
                ],
            },
            localVue,
        });
        expect(wrapper.vm.currentValue).toStrictEqual({ label: "test2", value: "2", default: true });
    });
    it("Sets default from defaultValue", async () => {
        const wrapper = mount(FormSelect, {
            propsData: {
                value: "2",
                defaultValue: "2",
                options: [
                    ["test1", "T", false],
                    ["test2", "2", false],
                ],
            },
            localVue,
        });
        expect(wrapper.vm.currentValue).toStrictEqual({ label: "test2", value: "2", default: false });
    });
    it("Changes value after new selection is made", async () => {
        const wrapper = mount(FormSelect, {
            propsData: {
                value: "T",
                defaultValue: "T",
                options: [
                    ["test1", "T", false],
                    ["test2", "2", false],
                ],
            },
            localVue,
        });

        const multiselect = wrapper.findComponent(Multiselect);
        // Manually trigger selection of the second item in optarray in the multiselect
        multiselect.vm.select(wrapper.vm.optArray[1]);
        expect(wrapper.emitted().input).toEqual([["2"]]);
    });
});
