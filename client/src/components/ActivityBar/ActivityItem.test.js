import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import mountTarget from "./ActivityItem.vue";

const localVue = getLocalVue();

describe("ActivityItem", () => {
    let wrapper;

    beforeEach(async () => {
        wrapper = mount(mountTarget, {
            propsData: {
                id: "activity-test-id",
                icon: "activity-test-icon",
                progressPercentage: 0,
                progressStatus: null,
                title: "activity-test-title",
                to: null,
                tooltip: "activity-test-tooltip",
            },
            localVue,
            stubs: {
                icon: { template: "<div></div>" },
            },
        });
    });

    it("rendering", async () => {
        const reference = wrapper.find("[id='activity-test-id']");
        expect(reference.attributes().id).toBe("activity-test-id");
        expect(reference.text()).toBe("activity-test-title");
        expect(reference.find("[icon='activity-test-icon']").exists()).toBeTruthy();
        expect(reference.find(".progress").exists()).toBeFalsy();
        await wrapper.setProps({ progressStatus: "success" });
        expect(reference.find(".progress").exists()).toBeTruthy();
        expect(reference.find(".bg-success").exists()).toBeTruthy();
        expect(reference.find(".progress-bar").element.style.width).toBe("0%");
        await wrapper.setProps({ progressPercentage: 50 });
        expect(reference.find(".progress-bar").element.style.width).toBe("50%");
        await wrapper.setProps({ progressStatus: "danger" });
        expect(reference.find(".bg-success").exists()).toBeFalsy();
        expect(reference.find(".bg-danger").exists()).toBeTruthy();
    });
});
