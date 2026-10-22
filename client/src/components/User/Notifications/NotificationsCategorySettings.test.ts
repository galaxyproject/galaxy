import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { UserNotificationPreferences } from "@/api/notifications";

import NotificationsCategorySettings from "./NotificationsCategorySettings.vue";

const localVue = getLocalVue();

function mountSettings(enabled: boolean) {
    const preferences = {
        message: { enabled, channels: { email: false, push: true } },
    } as unknown as UserNotificationPreferences;
    return mount(NotificationsCategorySettings as object, {
        props: { preferences, category: "message", supportedChannels: ["email", "push"] },
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
});
