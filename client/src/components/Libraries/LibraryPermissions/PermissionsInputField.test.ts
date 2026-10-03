import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Multiselect from "vue-multiselect";

import PermissionsInputField from "./PermissionsInputField.vue";

const QA_ROLE = { id: "role_id", name: "qa-role" };

const { getSelectOptions } = vi.hoisted(() => ({ getSelectOptions: vi.fn() }));

vi.mock("@/components/Libraries/LibraryPermissions/services", () => ({
    Services: class {
        getSelectOptions = getSelectOptions;
    },
}));

const PROPS = {
    id: "library_id",
    title: "Roles that can add items to this library",
    permission_type: "add_library_item_role_list",
    initial_value: [],
    apiRootUrl: "/api/libraries",
    alert: "",
};

describe("PermissionsInputField", () => {
    beforeEach(() => {
        getSelectOptions.mockReset();
        getSelectOptions.mockResolvedValue({ roles: [QA_ROLE], total: 1 });
    });

    it("reports the roles picked in the multiselect to its parent", async () => {
        // A real multiselect: a stub would lose its compat MODE 3 and take the Vue 2 v-model.
        const wrapper = mount(PermissionsInputField, {
            props: PROPS,
            global: getLocalVue(),
        });
        await flushPromises();

        // vue-multiselect 3 only emits update:modelValue, never the Vue 2 `input`.
        wrapper.findComponent(Multiselect).vm.$emit("update:modelValue", [QA_ROLE]);

        expect(wrapper.emitted("input")).toEqual([[[QA_ROLE], "add_library_item_role_list"]]);
    });

    describe("paging through roles", () => {
        let observed: { callback: IntersectionObserverCallback; element: Element } | undefined;

        beforeEach(() => {
            observed = undefined;
            vi.stubGlobal(
                "IntersectionObserver",
                class {
                    constructor(private callback: IntersectionObserverCallback) {}
                    observe(element: Element) {
                        observed = { callback: this.callback, element };
                    }
                    disconnect() {}
                },
            );
        });

        afterEach(() => {
            vi.unstubAllGlobals();
        });

        it("fetches the next page when the end of the list scrolls into view", async () => {
            getSelectOptions.mockResolvedValue({ roles: [QA_ROLE], total: 25 });
            const wrapper = mount(PermissionsInputField, { props: PROPS, global: getLocalVue() });
            await flushPromises();
            expect(getSelectOptions).toHaveBeenCalledTimes(1);

            // The list, and the sentinel at its end, only render while the dropdown is open.
            (wrapper.findComponent(Multiselect).vm as unknown as { activate: () => void }).activate();
            await flushPromises();

            expect(observed).toBeDefined();
            observed!.callback(
                [{ isIntersecting: true, target: observed!.element } as unknown as IntersectionObserverEntry],
                {} as IntersectionObserver,
            );
            await flushPromises();

            expect(getSelectOptions).toHaveBeenCalledTimes(2);
            // page 2 of 10 roles per page
            expect(getSelectOptions.mock.calls[1]!.slice(3, 5)).toEqual([2, 10]);
        });
    });
});
