import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import PermissionsInputField from "./PermissionsInputField.vue";

const API_ROOT_URL = "/api/libraries";
const LIBRARY_ID = "library_id";

const pending = {};

vi.mock("@/components/Libraries/LibraryPermissions/services", () => ({
    Services: class {
        getSelectOptions(apiRootUrl, id, isLibrary, page, pageLimit, searchValue) {
            return new Promise((resolve) => {
                pending[searchValue] = resolve;
            });
        }
    },
}));

function rolesResponse(names) {
    return { roles: names.map((name) => ({ id: name, name })), total: names.length };
}

describe("PermissionsInputField", () => {
    it("ignores search responses that arrive after a newer search", async () => {
        const wrapper = mount(PermissionsInputField, {
            localVue: getLocalVue(),
            propsData: {
                id: LIBRARY_ID,
                title: "Roles that can add items to this library",
                permission_type: "add_library_item_role_list",
                initial_value: [],
                apiRootUrl: API_ROOT_URL,
                alert: "alert",
            },
        });
        await flushPromises();
        pending[""](rolesResponse(["alice@test.test", "bob@test.test"]));
        await flushPromises();

        wrapper.vm.searchChanged("b");
        wrapper.vm.searchChanged("bob");
        await flushPromises();
        pending["bob"](rolesResponse(["bob@test.test"]));
        await flushPromises();
        pending["b"](rolesResponse(["alice@test.test", "bob@test.test"]));
        await flushPromises();

        expect(wrapper.vm.fetched_options.map((role) => role.name)).toEqual(["bob@test.test"]);
    });
});
