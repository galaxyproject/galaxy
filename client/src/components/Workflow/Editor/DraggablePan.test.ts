import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { mockOffset } from "./test_fixtures";

import Draggable from "./Draggable.vue";
import DraggablePan from "./DraggablePan.vue";

const localVue = getLocalVue();

describe("DraggablePan", () => {
    let pinia: ReturnType<typeof createPinia>;

    beforeEach(() => {
        pinia = createPinia();
        setActivePinia(pinia);
    });

    it("passes the end of a drag on to its parent", () => {
        // NodeOutput clears the editor's drag state on this event; if it never arrives,
        // the input terminals stay highlighted as drop targets after the drop.
        const onStop = vi.fn();
        const wrapper = mount(DraggablePan as object, {
            props: { rootOffset: mockOffset, onStop },
            global: {
                ...localVue,
                provide: { transform: ref({ x: 0, y: 0, k: 1 }), workflowId: "mock-workflow" },
            },
            pinia,
        });

        wrapper.findComponent(Draggable).vm.$emit("stop");

        expect(onStop).toHaveBeenCalledTimes(1);
    });
});
