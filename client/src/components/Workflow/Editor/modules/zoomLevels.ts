import type { Last } from "types/utilityTypes";

export const zoomLevels = [
    0.1, 0.2, 0.25, 0.33, 0.5, 0.67, 0.75, 0.8, 0.9, 1, 1.1, 1.25, 1.33, 1.5, 2, 2.5, 3, 4, 5,
] as const;

export type ZoomLevel = (typeof zoomLevels)[number];

export const minZoom = zoomLevels[0];
export const maxZoom = zoomLevels[zoomLevels.length - 1] as Last<typeof zoomLevels>;

/**
 * Finds the closest snapped zoom level
 * @param zoom decimal number indicating current zoom multiplier
 * @returns snapped zoom level
 */
export function getSnappedZoom(zoom: number): ZoomLevel {
    return zoomLevels.reduce((a, b) => {
        return Math.abs(b - zoom) < Math.abs(a - zoom) ? b : a;
    });
}

/**
 * Gets the next largest zoom level
 * @param zoom decimal number indicating current zoom multiplier
 * @returns snapped zoom level
 */
export function getZoomInLevel(zoom: number): ZoomLevel {
    const snapped = getSnappedZoom(zoom);
    const index = zoomLevels.indexOf(snapped);

    if (index === zoomLevels.length - 1) {
        return snapped;
    } else {
        return zoomLevels[index + 1] as ZoomLevel;
    }
}

/**
 * Get the next smaller zoom level
 * @param zoom decimal number indicating current zoom multiplier
 * @returns snapped zoom level
 */
export function getZoomOutLevel(zoom: number): ZoomLevel {
    const snapped = getSnappedZoom(zoom);
    const index = zoomLevels.indexOf(snapped);

    if (index === 0) {
        return snapped;
    } else {
        return zoomLevels[index - 1] as ZoomLevel;
    }
}

export function isMinZoom(zoom: number): boolean {
    return zoom === minZoom;
}

export function isMaxZoom(zoom: number): boolean {
    return zoom === maxZoom;
}
