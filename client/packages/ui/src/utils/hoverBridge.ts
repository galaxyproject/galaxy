import type { Rect } from "@floating-ui/dom";

export type Point = [number, number];

// Room for hand jitter where the pointer left the trigger; kept small, as it widens the area beside the trigger.
const EXIT_PADDING = 3;

function corners({ x, y, width, height }: Rect): Point[] {
    return [
        [x, y],
        [x + width, y],
        [x + width, y + height],
        [x, y + height],
    ];
}

function cross(origin: Point, a: Point, b: Point) {
    return (a[0] - origin[0]) * (b[1] - origin[1]) - (a[1] - origin[1]) * (b[0] - origin[0]);
}

// Andrew's monotone chain.
function convexHull(points: Point[]): Point[] {
    const sorted = [...points].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    const chain = (ordered: Point[]) => {
        const result: Point[] = [];
        for (const point of ordered) {
            while (result.length >= 2 && cross(result[result.length - 2]!, result[result.length - 1]!, point) <= 0) {
                result.pop();
            }
            result.push(point);
        }
        return result.slice(0, -1);
    };
    return [...chain(sorted), ...chain([...sorted].reverse())];
}

// Two points either side of the exit, set back into the element through the edge the pointer crossed.
function paddedExit([x, y]: Point, from: Rect): Point[] {
    const p = EXIT_PADDING;
    const edges: Array<[number, Point[]]> = [
        [
            Math.abs(y - from.y),
            [
                [x - p, y + p],
                [x + p, y + p],
            ],
        ],
        [
            Math.abs(y - (from.y + from.height)),
            [
                [x - p, y - p],
                [x + p, y - p],
            ],
        ],
        [
            Math.abs(x - from.x),
            [
                [x + p, y - p],
                [x + p, y + p],
            ],
        ],
        [
            Math.abs(x - (from.x + from.width)),
            [
                [x - p, y - p],
                [x - p, y + p],
            ],
        ],
    ];
    return edges.reduce((nearest, edge) => (edge[0] < nearest[0] ? edge : nearest))[1];
}

/**
 * The gap between two elements placed side by side, over the extent they share, as a polygon.
 * Empty when they touch, overlap or only meet diagonally.
 */
export function computeHoverGap(a: Rect, b: Rect): Point[] {
    const left = Math.max(a.x, b.x);
    const right = Math.min(a.x + a.width, b.x + b.width);
    const top = Math.max(a.y, b.y);
    const bottom = Math.min(a.y + a.height, b.y + b.height);
    if (left < right && bottom < top) {
        return corners({ x: left, y: bottom, width: right - left, height: top - bottom });
    }
    if (top < bottom && right < left) {
        return corners({ x: right, y: top, width: left - right, height: bottom - top });
    }
    return [];
}

// Whether `exit` lies in the half of `from` facing away from `to`.
function isFarSide([x, y]: Point, from: Rect, to: Rect) {
    if (to.y >= from.y + from.height) {
        return y < from.y + from.height / 2;
    }
    if (to.y + to.height <= from.y) {
        return y > from.y + from.height / 2;
    }
    if (to.x >= from.x + from.width) {
        return x < from.x + from.width / 2;
    }
    if (to.x + to.width <= from.x) {
        return x > from.x + from.width / 2;
    }
    return false;
}

/**
 * Where a pointer that left `from` at `exit` may travel on its way into `to` (safe triangle): the convex hull of
 * the exit point, the gap between the two elements and `to` itself, so every straight path from the exit into
 * `to` stays inside. It is only a polygon to test pointer positions against; nothing is laid over the page.
 * Empty when the pointer left through the half of `from` facing away from `to`: floating-ui's safePolygon drops
 * exits through the far edge, and this also drops those through the far half of the side edges.
 */
export function computeHoverBridge(exit: Point, from: Rect, to: Rect): Point[] {
    if (isFarSide(exit, from, to)) {
        return [];
    }
    return convexHull([exit, ...paddedExit(exit, from), ...computeHoverGap(from, to), ...corners(to)]);
}

// Ray casting; a point exactly on an edge may land on either side.
export function isPointInPolygon([x, y]: Point, polygon: Point[]) {
    let inside = false;
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
        const [xi, yi] = polygon[i]!;
        const [xj, yj] = polygon[j]!;
        if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) {
            inside = !inside;
        }
    }
    return inside;
}
