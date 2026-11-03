import { runInTestScope } from "@tests/vitest/effectScope";
import { describe, expect, it } from "vitest";
import { nextTick, ref } from "vue";

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
    it.each([
        { position: "start", scrollLeft: 0, fadeStart: false, fadeEnd: true },
        { position: "middle", scrollLeft: 100, fadeStart: true, fadeEnd: true },
        { position: "end", scrollLeft: 200, fadeStart: true, fadeEnd: false },
    ])("fades the hidden edges at the $position of the row", async ({ scrollLeft, fadeStart, fadeEnd }) => {
        const row = makeRow(300, 100);
        const edges = runInTestScope(() => useScrollEdges(ref(row)));
        await nextTick();

        scrollTo(row, 0);
        expect({ fadeStart: edges.fadeStart.value, fadeEnd: edges.fadeEnd.value }).toEqual({
            fadeStart: false,
            fadeEnd: true,
        });

        scrollTo(row, scrollLeft);

        expect({ fadeStart: edges.fadeStart.value, fadeEnd: edges.fadeEnd.value }).toEqual({ fadeStart, fadeEnd });
    });
});
