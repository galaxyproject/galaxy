// When merging forward: release_26.0+ runs vitest without globals and has neither tests/jest/helpers
// nor axios-mock-adapter, so this file merges cleanly but fails there. Port the test to vitest
// (vi.mock the Services class), and on release_26.1+ fold it into the existing PermissionsInputField.test.js.
// Drop this comment in the port.
import { mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import PermissionsInputField from "./PermissionsInputField";

const API_ROOT_URL = "/api/libraries";
const LIBRARY_ID = "library_id";

function rolesResponse(names) {
    return { roles: names.map((name) => ({ id: name, name })), total: names.length };
}

describe("PermissionsInputField", () => {
    const localVue = getLocalVue();
    let axiosMock;

    beforeEach(() => {
        axiosMock = new MockAdapter(axios);
    });

    afterEach(() => {
        axiosMock.restore();
    });

    it("ignores search responses that arrive after a newer search", async () => {
        const pending = {};
        axiosMock.onGet(new RegExp(`${API_ROOT_URL}/${LIBRARY_ID}/permissions`)).reply((config) => {
            const query = new URLSearchParams(config.url.split("?")[1]).get("q") || "";
            return new Promise((resolve) => {
                pending[query] = resolve;
            });
        });
        const wrapper = mount(PermissionsInputField, {
            localVue,
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
        pending[""]([200, rolesResponse(["alice@test.test", "bob@test.test"])]);
        await flushPromises();

        wrapper.vm.searchChanged("b");
        wrapper.vm.searchChanged("bob");
        await flushPromises();
        pending["bob"]([200, rolesResponse(["bob@test.test"])]);
        await flushPromises();
        pending["b"]([200, rolesResponse(["alice@test.test", "bob@test.test"])]);
        await flushPromises();

        expect(wrapper.vm.fetched_options.map((role) => role.name)).toEqual(["bob@test.test"]);
    });
});
