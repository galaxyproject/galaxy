import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { NotificationCategory, UserNotificationPreferences } from "@/api/notifications";

import NotificationsCategorySettings from "./NotificationsCategorySettings.vue";

const localVue = getLocalVue();

function mountSettings(enabled: boolean, category: NotificationCategory = "message") {
    const preferences = {
        [category]: { enabled, channels: { email: false, push: true } },
    } as unknown as UserNotificationPreferences;
    return mount(NotificationsCategorySettings as object, {
        props: { preferences, category, supportedChannels: ["email", "push"] },
        global: localVue,
    });
}

describe("NotificationsCategorySettings", () => {
    it("emits the category toggle with its new value", async () => {
        const wrapper = mountSettings(false);
        const [categorySwitch] = wrapper.findAll<HTMLInputElement>("input[type='checkbox']");

        expect(categorySwitch!.attributes("role")).toBe("switch");
        await categorySwitch!.setValue(true);

        expect(wrapper.emitted("onCategoryEnabledChange")).toEqual([["message", true]]);
    });

    it("emits a channel change and disables channels of a disabled category", async () => {
        const wrapper = mountSettings(true);
        const [, emailCheckbox, pushCheckbox] = wrapper.findAll<HTMLInputElement>("input[type='checkbox']");

        expect(emailCheckbox!.element.checked).toBe(false);
        expect(pushCheckbox!.element.checked).toBe(true);
        await emailCheckbox!.setValue(true);

        expect(wrapper.emitted("onChannelChange")).toEqual([["message", "email", true]]);

        await wrapper.findAll("input[type='checkbox']")[0]!.setValue(false);

        expect(emailCheckbox!.element.disabled).toBe(true);
        expect(pushCheckbox!.element.disabled).toBe(true);
    });

    it("shows only the channel toggles for job_completion, which is opted into for each run", async () => {
        const wrapper = mountSettings(true, "job_completion");
        const checkboxes = wrapper.findAll<HTMLInputElement>("input[type='checkbox']");

        expect(checkboxes.map((checkbox) => checkbox.attributes("role"))).not.toContain("switch");
        expect(checkboxes).toHaveLength(2);
        await checkboxes[0]!.setValue(true);

        expect(wrapper.emitted("onChannelChange")).toEqual([["job_completion", "email", true]]);
    });
});
