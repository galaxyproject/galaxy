/**
 * Shared SVG path generation utilities for graph edge rendering.
 *
 * - curveBasisPath: smooth bezier curves via d3 curveBasis (used by the workflow editor)
 * - computeControlPoints: bezier control points for a connection between two endpoints
 */

import { curveBasis, line } from "d3";

// ── curveBasis rendering ──

const _curveBasisLine = line().curve(curveBasis);

/**
 * Render points as a smooth bezier curve using d3's curveBasis interpolation.
 * Used by the workflow editor for connections between nodes.
 */
export function curveBasisPath(points: [number, number][]): string {
    return _curveBasisLine(points) ?? "";
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
