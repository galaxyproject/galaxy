import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import FormSelect from "./FormSelect";
import flushPromises from "flush-promises";

const localVue = getLocalVue();

// describe("FormSelect", () => {
//     const mountFormSelect = async (props) =>
//         await mount(FormSelect, {
//             propsData: props,
//             localVue,
//         });
    // const getInput = async (wrapper) => await wrapper.find("input[type='select']");

//     it("input should be rendered with select type", async () => {
//         const wrapper = await mountFormSelect({
//             value: "T",
//             defaultValue: "T",
//             options: [["test1", "T", true], ["test2", "2", false]]
//         });
//         await flushPromises();
//         const input = await getInput(wrapper);
//         console.log(wrapper);
//         console.log(input);
//         expect(input.exists()).toBe(true);
//     });
// });

describe("FormSelect", () => {
    it("Sets default currentValue as first option when not told otherwise", async () => {
        let wrapper;
        wrapper = mount(FormSelect, {
            propsData: {
                value: "",
                defaultValue: "",
                options: [["test1", "T", false], ["test2", "2", false]],
            },
            localVue,
        });
        const input = wrapper.find("input");
        expect(wrapper.vm.currentValue).toStrictEqual({"label": "test1", "value": "T", "default": false});
    })
    it("Sets default currentValue to object with 'default: true' when default not provided from defaultValue", async () => {
        let wrapper;
        wrapper = mount(FormSelect, {
            propsData: {
                value: "",
                defaultValue: "",
                options: [["test1", "T", false], ["test2", "2", true]],
            },
            localVue,
        });
        const input = wrapper.find("input");
        expect(wrapper.vm.currentValue).toStrictEqual({"label": "test2", "value": "2", "default": true});
    })
    it("Sets default from defaultValue", async () => {
        let wrapper;
        wrapper = mount(FormSelect, {
            propsData: {
                value: "2",
                defaultValue: "2",
                options: [["test1", "T", false], ["test2", "2", false]],
            },
            localVue,
        });
        const input = wrapper.find("input");
        expect(wrapper.vm.currentValue).toStrictEqual({"label": "test1", "value": "T", "default": false});
    })
    it("Returns a new value after being switched over", async() => {
        let wrapper;
        wrapper = mount(FormSelect, {
            propsData: {
                value: "",
                defaultValue: "",
                options: [["test1", "T", false], ["test2", "2", false]],
            },
            localVue,
        });
        wrapper.setValue()
    }
});