import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import PermissionsInputField from "./PermissionsInputField.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";

vi.mock("@/components/Libraries/LibraryPermissions/services", () => ({
    Services: class {
        getSelectOptions() {
            return Promise.resolve({ roles: [], total: 0 });
        }
    },
}));

describe("PermissionsInputField", () => {
    beforeEach(() => {
        vi.mocked(sanitizeHtml).mockClear();
    });

    it("renders the alert through v-sanitize-html", () => {
        const alert = "Users with <strong>any</strong> of these roles can access";

        const wrapper = shallowMount(PermissionsInputField, {
            props: {
                id: "lib1",
                title: "Access",
                permission_type: "access",
                initial_value: [],
                apiRootUrl: "/api/libraries",
                alert,
            },
            global: getLocalVue(),
        });

        expect(sanitizeHtml).toHaveBeenCalledWith(alert, "default");
        expect(wrapper.findComponent(GAlert).find("strong").text()).toBe("any");
    });
});
