import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";
import Multiselect from "vue-multiselect";

import PermissionsInputField from "./PermissionsInputField.vue";

const QA_ROLE = { id: "role_id", name: "qa-role" };

vi.mock("@/components/Libraries/LibraryPermissions/services", () => ({
    Services: class {
        getSelectOptions() {
            return Promise.resolve({ roles: [QA_ROLE], total: 1 });
        }
    },
}));

describe("PermissionsInputField", () => {
    it("reports the roles picked in the multiselect to its parent", async () => {
        // A real multiselect: a stub would lose its compat MODE 3 and take the Vue 2 v-model.
        const wrapper = mount(PermissionsInputField, {
            props: {
                id: "library_id",
                title: "Roles that can add items to this library",
                permission_type: "add_library_item_role_list",
                initial_value: [],
                apiRootUrl: "/api/libraries",
                alert: "",
            },
            global: getLocalVue(),
        });
        await flushPromises();

        // vue-multiselect 3 only emits update:modelValue, never the Vue 2 `input`.
        wrapper.findComponent(Multiselect).vm.$emit("update:modelValue", [QA_ROLE]);

        expect(wrapper.emitted("input")).toEqual([[[QA_ROLE], "add_library_item_role_list"]]);
    });
});
