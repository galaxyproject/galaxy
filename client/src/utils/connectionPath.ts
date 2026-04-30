/**
 * Shared SVG path generation utilities for graph edge rendering.
 *
 * Two rendering strategies:
 * - curveBasisPath: smooth bezier curves via d3 curveBasis (used by workflow editor)
 * - orthogonalPath: straight segments with arc-rounded bends (used for ELK-routed graphs)
 *
 * Both accept point arrays and return SVG path `d` attribute strings.
 */

import { curveBasis, line } from "d3";

/** Point with x/y coordinates */
export interface PathPoint {
    x: number;
    y: number;
}

// ── curveBasis rendering ──

const _curveBasisLine = line().curve(curveBasis);

/**
 * Render points as a smooth bezier curve using d3's curveBasis interpolation.
 * Used by the workflow editor for connections between nodes.
 */
export function curveBasisPath(points: [number, number][]): string {
    return _curveBasisLine(points) ?? "";
}

// ── Orthogonal rendering with arc bends ──

const DEFAULT_RADIUS = 8;

/**
 * Render orthogonal edge points as an SVG path with rounded corners.
 * Uses arc segments at each bend point to produce smooth turns while
 * faithfully following the layout engine's routing.
 *
 * Used for ELK-routed graph edges where points form orthogonal paths.
 */
export function orthogonalPath(points: PathPoint[], radius: number = DEFAULT_RADIUS): string {
    if (points.length < 2) {
        return "";
    }
    if (points.length === 2) {
        return `M ${points[0]!.x} ${points[0]!.y} L ${points[1]!.x} ${points[1]!.y}`;
    }

    const parts: string[] = [`M ${points[0]!.x} ${points[0]!.y}`];

    for (let i = 1; i < points.length - 1; i++) {
        const prev = points[i - 1]!;
        const curr = points[i]!;
        const next = points[i + 1]!;

        const dx1 = prev.x - curr.x;
        const dy1 = prev.y - curr.y;
        const dx2 = next.x - curr.x;
        const dy2 = next.y - curr.y;

        const d1 = Math.sqrt(dx1 * dx1 + dy1 * dy1);
        const d2 = Math.sqrt(dx2 * dx2 + dy2 * dy2);

        const r = Math.min(radius, d1 / 2, d2 / 2);

        const startX = curr.x + (dx1 / d1) * r;
        const startY = curr.y + (dy1 / d1) * r;
        const endX = curr.x + (dx2 / d2) * r;
        const endY = curr.y + (dy2 / d2) * r;

        const cross = dx1 * dy2 - dy1 * dx2;
        const sweep = cross > 0 ? 0 : 1;

        parts.push(`L ${startX} ${startY}`);
        parts.push(`A ${r} ${r} 0 0 ${sweep} ${endX} ${endY}`);
    }

    const last = points[points.length - 1]!;
    parts.push(`L ${last.x} ${last.y}`);

    return parts.join(" ");
}

// ── Control point computation ──

const BASE_LINE_SHIFT = 15;
const LINE_SHIFT_GROW_X = 0.15;
const LINE_SHIFT_GROW_Y = 0.08;

/**
 * Compute bezier control points for a connection between two endpoints.
 * Uses the same algorithm as the Galaxy workflow editor (SVGConnection.vue):
 * forward connections get 4 control points, backward connections get 6
 * for smoother curves.
 */
export function computeControlPoints(startX: number, startY: number, endX: number, endY: number): [number, number][] {
    const forward = endX >= startX;
    const distX = Math.abs(endX - startX - BASE_LINE_SHIFT);
    const distY = Math.abs(endY - startY);

    let shiftX: number;
    if (forward) {
        shiftX = BASE_LINE_SHIFT + distX * LINE_SHIFT_GROW_X + distY * LINE_SHIFT_GROW_Y;
    } else {
        shiftX = BASE_LINE_SHIFT * 2 + distX * LINE_SHIFT_GROW_X * 0.5 + distY * LINE_SHIFT_GROW_Y * 0.5;
    }

    if (forward) {
        return [
            [startX, startY],
            [startX + shiftX, startY],
            [endX - shiftX, endY],
            [endX, endY],
        ];
    } else {
        const shiftY = (endY - startY) / 2;
        return [
            [startX, startY],
            [startX + shiftX, startY],
            [startX + shiftX, startY + shiftY],
            [endX - shiftX, endY - shiftY],
            [endX - shiftX, endY],
            [endX, endY],
        ];
    }
}
