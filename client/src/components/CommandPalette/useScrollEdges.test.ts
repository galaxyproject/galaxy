import { describe, expect, it } from "vitest";
import { effectScope, nextTick, ref } from "vue";

import { useScrollEdges } from "./useScrollEdges";

/** The test DOM has no layout, so the row gets fixed scroll metrics */
function makeRow(scrollWidth: number, clientWidth: number): HTMLElement {
    const row = document.createElement("div");
    Object.defineProperty(row, "scrollWidth", { value: scrollWidth });
    Object.defineProperty(row, "clientWidth", { value: clientWidth });
    return row;
}

function scrollTo(row: HTMLElement, left: number) {
    Object.defineProperty(row, "scrollLeft", { value: left, configurable: true });
    row.dispatchEvent(new Event("scroll"));
}

describe("useScrollEdges", () => {
    it("fades whichever edge hides content as the row scrolls", async () => {
        const row = makeRow(300, 100);
        const scope = effectScope();
        const edges = scope.run(() => useScrollEdges(ref(row)))!;
        await nextTick();

        scrollTo(row, 0);
        expect([edges.fadeStart.value, edges.fadeEnd.value]).toEqual([false, true]);

        scrollTo(row, 100);
        expect([edges.fadeStart.value, edges.fadeEnd.value]).toEqual([true, true]);

        scrollTo(row, 200);
        expect([edges.fadeStart.value, edges.fadeEnd.value]).toEqual([true, false]);

        scope.stop();
    });
});
