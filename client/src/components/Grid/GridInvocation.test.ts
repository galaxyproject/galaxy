import { createTestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { useUserStore } from "@/stores/userStore";

import type { GridConfig } from "./configs/types";

import GridInvocation from "./GridInvocation.vue";
import GridList from "./GridList.vue";

function mountedConfig(ownerGrid: boolean): GridConfig {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    useUserStore(pinia).currentUser = getFakeRegisteredUser();
    const wrapper = shallowMount(GridInvocation as object, {
        props: { ownerGrid },
        global: { ...getLocalVue(), plugins: [pinia] },
    });
    return wrapper.findComponent(GridList).props("gridConfig") as GridConfig;
}

describe("GridInvocation", () => {
    it("offers filters on the user's own invocation grid", () => {
        const config = mountedConfig(true);
        expect(config.filtering).toBeDefined();
        expect(config.fields.filter((field) => field.filter).map((field) => field.key)).toEqual([
            "workflow_id",
            "history_id",
        ]);
    });

    it("offers no filters on the admin grid, whose lookups only cover the admin's own items", () => {
        const config = mountedConfig(false);
        expect(config.filtering).toBeUndefined();
        expect(config.fields.filter((field) => field.filter)).toEqual([]);
    });
});
