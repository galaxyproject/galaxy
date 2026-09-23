import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import PermissionsInputField from "./PermissionsInputField.vue";

vi.mock("@/components/Libraries/LibraryPermissions/services", () => ({
    Services: class {
        getSelectOptions() {
            return Promise.resolve({ roles: [], total: 0 });
        }
    },
}));

describe("PermissionsInputField", () => {
    it("renders the alert through v-sanitize-html", () => {
        vi.mocked(sanitizeHtml).mockClear();
        const alert = "Users with <strong>any</strong> of these roles can access";
        const wrapper = shallowMount(PermissionsInputField, {
            localVue: getLocalVue(),
            propsData: {
                id: "lib1",
                title: "Access",
                permission_type: "access",
                initial_value: [],
                apiRootUrl: "/api/libraries",
                alert,
            },
        });

        expect(sanitizeHtml).toHaveBeenCalledWith(alert, "default");
        expect(wrapper.find("strong").text()).toBe("any");
    });
});
