import type { Rect } from "@floating-ui/dom";
import { describe, expect, it } from "vitest";

import { computeHoverBridge, computeHoverGap, isPointInPolygon, type Point } from "./hoverBridge";

function within({ x, y, width, height }: Rect, [px, py]: Point) {
    return px >= x && px <= x + width && py >= y && py <= y + height;
}

function spread({ x, y, width, height }: Rect): Point[] {
    return [0.01, 0.25, 0.5, 0.75, 0.99].flatMap((u) =>
        [0.01, 0.5, 0.99].map((v) => [x + u * width, y + v * height] as Point),
    );
}

// Just outside each edge, where a pointer leaving the element is first reported.
function exitPoints({ x, y, width, height }: Rect): Point[] {
    return [0.1, 0.5, 0.9].flatMap((u) => [
        [x + u * width, y - 0.5] as Point,
        [x + u * width, y + height + 0.5] as Point,
        [x - 0.5, y + u * height] as Point,
        [x + width + 0.5, y + u * height] as Point,
    ]);
}

// Walks straight lines from every exit point that gets a bridge into the target, returning the first point over
// neither element nor the bridge.
function findDeadSpot(from: Rect, to: Rect) {
    for (const exit of exitPoints(from)) {
        const bridge = computeHoverBridge(exit, from, to);
        if (!bridge.length) {
            continue;
        }
        for (const [bx, by] of spread(to)) {
            for (let t = 0.02; t <= 1; t += 0.02) {
                const point: Point = [exit[0] + (bx - exit[0]) * t, exit[1] + (by - exit[1]) * t];
                if (!within(from, point) && !within(to, point) && !isPointInPolygon(point, bridge)) {
                    return { exit, point };
                }
            }
        }
    }
    return null;
}

// A 24px button at the start of a row of buttons, with a 276px popover 10px below it (Node.vue's recommendations).
const trigger = { x: 134, y: 0, width: 24, height: 20 };
const popover = { x: 8, y: 30, width: 276, height: 100 };

describe("computeHoverBridge", () => {
    it("covers the gap and the popover when leaving towards it", () => {
        const bridge = computeHoverBridge([146, 20.5], trigger, popover);

        expect(isPointInPolygon([146, 25], bridge)).toBe(true);
        expect(isPointInPolygon([60, 29], bridge)).toBe(true);
        expect(isPointInPolygon([146, 80], bridge)).toBe(true);
    });

    it("leaves the controls beside the trigger out", () => {
        const bridge = computeHoverBridge([146, 20.5], trigger, popover);

        expect(isPointInPolygon([170, 10], bridge)).toBe(false);
        expect(isPointInPolygon([170, 18], bridge)).toBe(false);
        expect(isPointInPolygon([120, 10], bridge)).toBe(false);
    });

    it("keeps a sideways exit along the row only for a few pixels", () => {
        const bridge = computeHoverBridge([158.5, 10], trigger, popover);

        expect(isPointInPolygon([162, 10], bridge)).toBe(true);
        expect(isPointInPolygon([180, 10], bridge)).toBe(false);
        expect(isPointInPolygon([200, 10], bridge)).toBe(false);
    });

    it.each<[string, Point]>([
        ["the far edge", [146, -0.5]],
        ["the far half of a side edge", [158.5, 9]],
        ["the far half of the other side edge", [133.5, 4]],
    ])("drops an exit through %s", (_edge, exit) => {
        expect(computeHoverBridge(exit, trigger, popover)).toEqual([]);
    });

    it("keeps an exit through the near half of a side edge", () => {
        expect(computeHoverBridge([158.5, 11], trigger, popover)).not.toEqual([]);
    });

    it.each<[string, Rect, Rect, Point]>([
        ["top-start", { x: 50, y: 200, width: 20, height: 20 }, { x: 0, y: 90, width: 120, height: 100 }, [60, 220.5]],
        ["right", { x: 0, y: 50, width: 20, height: 20 }, { x: 30, y: 0, width: 100, height: 150 }, [-0.5, 60]],
        ["left-end", { x: 200, y: 10, width: 20, height: 20 }, { x: 90, y: 0, width: 100, height: 60 }, [220.5, 20]],
    ])("drops an exit through the far edge from a %s popover", (_placement, from, to, exit) => {
        expect(computeHoverBridge(exit, from, to)).toEqual([]);
    });

    it("covers a slow diagonal that leaves the trigger through its side edge", () => {
        const icon = { x: 0, y: 0, width: 16, height: 16 };
        const wide = { x: 0, y: 26, width: 276, height: 100 };
        // Centre to centre, leaving the icon's right edge at y ~12.
        const path = (t: number): Point => [8 + 130 * t, 8 + 68 * t];
        const bridge = computeHoverBridge(path(0.062), icon, wide);

        for (let t = 0.07; t < 0.27; t += 0.01) {
            expect(isPointInPolygon(path(t), bridge)).toBe(true);
        }
    });

    it.each<[string, Rect, Rect]>([
        ["bottom-start", { x: 0, y: 0, width: 16, height: 16 }, { x: 0, y: 26, width: 276, height: 100 }],
        ["top-start", { x: 50, y: 200, width: 20, height: 20 }, { x: 0, y: 90, width: 120, height: 100 }],
        ["right", { x: 0, y: 50, width: 20, height: 20 }, { x: 30, y: 0, width: 100, height: 150 }],
        ["left-end", { x: 200, y: 10, width: 20, height: 20 }, { x: 90, y: 0, width: 100, height: 60 }],
        ["bottom, wider trigger", { x: 0, y: 0, width: 300, height: 20 }, { x: 100, y: 30, width: 100, height: 50 }],
    ])("leaves no dead spot on a straight path into a %s popover", (_placement, from, to) => {
        expect(findDeadSpot(from, to)).toBeNull();
    });
});

describe("computeHoverGap", () => {
    it("spans the gap over the extent both elements share", () => {
        expect(computeHoverGap(trigger, popover)).toEqual([
            [134, 20],
            [158, 20],
            [158, 30],
            [134, 30],
        ]);
        expect(
            computeHoverGap({ x: 0, y: 50, width: 20, height: 20 }, { x: 30, y: 0, width: 100, height: 150 }),
        ).toEqual([
            [20, 50],
            [30, 50],
            [30, 70],
            [20, 70],
        ]);
    });

    it("is empty when the elements touch or only meet diagonally", () => {
        expect(computeHoverGap(trigger, { ...popover, y: 20 })).toEqual([]);
        expect(computeHoverGap(trigger, { x: 200, y: 40, width: 50, height: 50 })).toEqual([]);
    });
});
