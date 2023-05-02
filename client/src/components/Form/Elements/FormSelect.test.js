import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import MountTarget from "./FormSelect";

const localVue = getLocalVue(true);

function createTarget(propsData) {
    return mount(MountTarget, {
        propsData,
        localVue,
    });
}

describe("FormSelect", () => {
    it("basics", async () => {
        const wrapper = createTarget({
            value: "value_1",
            options: [
                ["label_1", "value_1"],
                ["label_2", "value_2"],
                ["label_3", "value_3"],
            ],
        });
        const target = wrapper.findComponent(MountTarget);
        const options = target.findAll("li > span > span");
        expect(options.length).toBe(3);
        for (let i = 0; i < options.length; i++) {
            expect(options.at(i).text()).toBe(`label_${i + 1}`);
        }
    });
});
