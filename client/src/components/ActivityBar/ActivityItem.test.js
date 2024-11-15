import { createTestingPinia } from "@pinia/testing";
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
                activityBarId: "activity-bar-test-id",
                icon: "activity-test-icon",
                indicator: 0,
                progressPercentage: 0,
                progressStatus: null,
                title: "activity-test-title",
                to: null,
                tooltip: "activity-test-tooltip",
            },
            pinia: createTestingPinia(),
            localVue,
            stubs: {
                FontAwesomeIcon: true,
            },
        });
    });

    it("rendering", async () => {
        const reference = wrapper.find(".activity-item");
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

    it("rendering indicator", async () => {
        const reference = wrapper.find(".activity-item");
        const indicatorSelector = "[data-description='activity indicator']";
        const noindicator = reference.find(indicatorSelector);
        expect(noindicator.exists()).toBeFalsy();
        await wrapper.setProps({ indicator: 1 });
        const indicator = reference.find(indicatorSelector);
        expect(indicator.exists()).toBeTruthy();
        expect(indicator.text()).toBe("1");
        await wrapper.setProps({ indicator: 1000 });
        const maxindicator = reference.find(indicatorSelector);
        expect(maxindicator.text()).toBe("99");
    });
});
