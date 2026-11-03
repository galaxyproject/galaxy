import flushPromises from "flush-promises";
import { afterEach, describe, expect, it, vi } from "vitest";
import { effectScope, nextTick, ref } from "vue";

import { useFloatingPosition } from "./floatingPosition";

const floatingUi = vi.hoisted(() => ({
    result: { x: 12, y: 34, placement: "top-start", middlewareData: { arrow: { x: 5 } } },
    stopTracking: vi.fn(),
    pending: null as Promise<unknown> | null,
}));

vi.mock("@floating-ui/dom", () => ({
    computePosition: () => floatingUi.pending ?? Promise.resolve(floatingUi.result),
    autoUpdate: (_reference: unknown, _floating: unknown, update: () => void) => {
        update();
        return floatingUi.stopTracking;
    },
}));

function setupFloatingPosition({ active: initiallyActive }: { active: boolean }) {
    const reference = document.createElement("button");
    const floating = ref<HTMLElement>(document.createElement("div"));
    const active = ref(initiallyActive);
    const scope = effectScope();
    const position = scope.run(() => useFloatingPosition(reference, floating, active, () => ({})))!;
    return { active, position, scope };
}

/** Holds computePosition's result back until the returned function releases it. */
function holdComputedPosition() {
    let release = () => {};
    floatingUi.pending = new Promise((resolve) => (release = () => resolve(floatingUi.result)));
    return release;
}

type FloatingPosition = ReturnType<typeof setupFloatingPosition>["position"];

function expectComputedPosition(position: FloatingPosition) {
    expect(position.x.value).toBe(12);
    expect(position.y.value).toBe(34);
    expect(position.placement.value).toBe("top-start");
    expect(position.middlewareData.value.arrow?.x).toBe(5);
}

describe("useFloatingPosition", () => {
    afterEach(() => {
        floatingUi.stopTracking.mockClear();
        floatingUi.pending = null;
    });

    it("positions a floating element that is active from the start", async () => {
        const { position } = setupFloatingPosition({ active: true });

        await vi.waitFor(() => expect(position.x.value).toBe(12));

        expectComputedPosition(position);
    });

    it("positions the floating element once it becomes active", async () => {
        const { active, position } = setupFloatingPosition({ active: false });

        active.value = true;
        await vi.waitFor(() => expect(position.x.value).toBe(12));

        expectComputedPosition(position);
    });

    it("discards a position that resolves after tracking stopped", async () => {
        const release = holdComputedPosition();
        const { active, position } = setupFloatingPosition({ active: true });

        active.value = false;
        await nextTick();
        release();
        await flushPromises();

        expect(position.x.value).toBe(0);
        expect(position.y.value).toBe(0);
        expect(position.placement.value).toBe("bottom");
    });

    it("stops tracking when deactivated", async () => {
        const { active } = setupFloatingPosition({ active: false });
        active.value = true;
        await nextTick();
        expect(floatingUi.stopTracking).not.toHaveBeenCalled();

        active.value = false;
        await nextTick();

        expect(floatingUi.stopTracking).toHaveBeenCalledTimes(1);
    });

    it("stops tracking when its scope is disposed", async () => {
        const { active, scope } = setupFloatingPosition({ active: false });
        active.value = true;
        await nextTick();
        expect(floatingUi.stopTracking).not.toHaveBeenCalled();

        scope.stop();

        expect(floatingUi.stopTracking).toHaveBeenCalledTimes(1);
    });

    it("settles whenPositioned only once the pending position is applied", async () => {
        const release = holdComputedPosition();
        const { active, position } = setupFloatingPosition({ active: false });
        active.value = true;
        await nextTick();

        const positioned = vi.fn();
        position.whenPositioned().then(positioned);
        await flushPromises();
        expect(positioned).not.toHaveBeenCalled();

        release();
        await vi.waitFor(() => expect(positioned).toHaveBeenCalled());

        expect(position.x.value).toBe(12);
    });
});
