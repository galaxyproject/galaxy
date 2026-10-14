import { shallowMount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import CollectionOperations from "./CollectionOperations.vue";

vi.mock("vue-router", () => ({ useRoute: () => ({ fullPath: "/" }) }));

function offersExport(elementsStates: Record<string, number>) {
    const wrapper = shallowMount(CollectionOperations as object, {
        props: {
            dsc: {
                id: "dsc_1",
                history_id: "hist_1",
                name: "reads",
                populated_state: "ok",
                visible: true,
                deleted: false,
                elements_states: elementsStates,
            },
        },
        global: { renderStubDefaultSlot: true },
    });
    return wrapper.findComponent({ name: "ExportToAnotherGalaxy" }).exists();
}

describe("CollectionOperations", () => {
    it("offers Export only once every element is ok", () => {
        expect(offersExport({ ok: 3 })).toBe(true);
        expect(offersExport({ ok: 3, running: 0 })).toBe(true);
        expect(offersExport({ ok: 2, running: 1 })).toBe(false);
        expect(offersExport({ ok: 2, queued: 1 })).toBe(false);
        expect(offersExport({ ok: 2, error: 1 })).toBe(false);
    });
});
