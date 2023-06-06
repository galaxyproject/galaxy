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
                description: "activity-test-description",
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
        expect(wrapper.attributes().description).toBe("activity-test-description");
        expect(wrapper.find("li").attributes().id).toBe("activity-test-id");
        expect(wrapper.find("li").text()).toBe("activity-test-title");
        expect(wrapper.find("[icon='activity-test-icon']").exists()).toBeTruthy();
        expect(wrapper.find(".progress").exists()).toBeFalsy();
        await wrapper.setProps({ progressStatus: "success" });
        expect(wrapper.find(".progress").exists()).toBeTruthy();
        expect(wrapper.find(".bg-success").exists()).toBeTruthy();
        expect(wrapper.find(".progress-bar").element.style.width).toBe("0%");
        await wrapper.setProps({ progressPercentage: 50 });
        expect(wrapper.find(".progress-bar").element.style.width).toBe("50%");
        await wrapper.setProps({ progressStatus: "danger" });
        expect(wrapper.find(".bg-success").exists()).toBeFalsy();
        expect(wrapper.find(".bg-danger").exists()).toBeTruthy();
    });
});
