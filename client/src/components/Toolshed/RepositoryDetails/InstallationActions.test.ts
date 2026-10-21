import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import InstallationActions from "./InstallationActions.vue";

describe("InstallationActions", () => {
    it("names the busy button while an action is running", () => {
        const wrapper = mount(InstallationActions as object, {
            props: { isBusy: true },
            global: getLocalVue(),
        });
        const button = wrapper.get("button");
        expect(button.attributes("aria-busy")).toBe("true");
        expect(button.attributes("title")).toBe("Working...");
    });
});
