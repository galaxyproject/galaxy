import { afterEach, describe, expect, it, vi } from "vitest";
import { effectScope, nextTick, ref } from "vue";

import { useFloatingPosition } from "./floatingPosition";

const floatingUi = vi.hoisted(() => ({
    position: { x: 12, y: 34, placement: "top-start", middlewareData: { arrow: { x: 5 } } },
    stopTracking: vi.fn(),
    pending: null as Promise<unknown> | null,
}));

vi.mock("@floating-ui/dom", () => ({
    computePosition: () => floatingUi.pending ?? Promise.resolve(floatingUi.position),
    autoUpdate: (_reference: unknown, _floating: unknown, update: () => void) => {
        update();
        return floatingUi.stopTracking;
    },
}));

function setup(initiallyActive: boolean) {
    const reference = document.createElement("button");
    const floating = ref<HTMLElement>(document.createElement("div"));
    const active = ref(initiallyActive);
    const scope = effectScope();
    const position = scope.run(() => useFloatingPosition(reference, floating, active, () => ({})))!;
    return { active, position, scope };
}

describe("useFloatingPosition", () => {
    afterEach(() => {
        floatingUi.stopTracking.mockClear();
        floatingUi.pending = null;
    });

    it("positions a floating element that is active from the start", async () => {
        const { position } = setup(true);

        await vi.waitFor(() => expect(position.x.value).toBe(12));
    });

    it("discards a position that resolves after tracking stopped", async () => {
        let resolve: (value: unknown) => void = () => {};
        floatingUi.pending = new Promise((r) => (resolve = r));
        const { active, position } = setup(true);

        active.value = false;
        await nextTick();
        resolve(floatingUi.position);
        await new Promise((settled) => setTimeout(settled));

        expect(position.x.value).toBe(0);
    });

    it("positions the floating element once it becomes active", async () => {
        const { active, position } = setup(false);

        active.value = true;
        await vi.waitFor(() => expect(position.x.value).toBe(12));

        expect(position.y.value).toBe(34);
        expect(position.placement.value).toBe("top-start");
        expect(position.middlewareData.value.arrow?.x).toBe(5);
    });

    it("stops tracking when deactivated", async () => {
        const { active } = setup(false);
        active.value = true;
        await nextTick();

        active.value = false;
        await nextTick();

        expect(floatingUi.stopTracking).toHaveBeenCalledTimes(1);
    });

    it("stops tracking when its scope is disposed", async () => {
        const { active, scope } = setup(false);
        active.value = true;
        await nextTick();

        scope.stop();

        expect(floatingUi.stopTracking).toHaveBeenCalledTimes(1);
    });

    it("settles whenPositioned only once the pending position is applied", async () => {
        let resolve: (value: unknown) => void = () => {};
        floatingUi.pending = new Promise((r) => (resolve = r));
        const { active, position } = setup(false);
        active.value = true;
        await nextTick();

        const positioned = vi.fn();
        position.whenPositioned().then(positioned);
        await new Promise((settled) => setTimeout(settled));
        expect(positioned).not.toHaveBeenCalled();

        resolve(floatingUi.position);
        await vi.waitFor(() => expect(positioned).toHaveBeenCalled());
        expect(position.x.value).toBe(12);
    });
});
