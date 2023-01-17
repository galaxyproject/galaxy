import type { ZoomTransform } from "d3-zoom";
import type { ElementBounding } from "./useCoordinatePosition";

const MIN_OFFSET = -50;
const MAX_OFFSET = 50;
const NODE_WIDTH = 200;
const NODE_HEIGHT = 50;
// To insert a node close to the center (+/- 50px) of the canvas
// we subtract 100 from MIN/MAX (which are just guesses, they're defined in REM)
const MIN_OFFSET_SHIFT_X = MIN_OFFSET - NODE_WIDTH / 2;
const MAX_OFFSET_SHIFT_X = MAX_OFFSET - NODE_WIDTH / 2;
const MIN_OFFSET_SHIFT_Y = MIN_OFFSET - NODE_HEIGHT / 2;
const MAX_OFFSET_SHIFT_Y = MAX_OFFSET - NODE_HEIGHT / 2;

export function defaultPosition(rootOffset: ElementBounding, transform: ZoomTransform) {
    const left =
        (-transform.x + rootOffset.width / 2 + randomInteger(MIN_OFFSET_SHIFT_X, MAX_OFFSET_SHIFT_X)) / transform.k;
    const top =
        (-transform.y + rootOffset.height / 2 + randomInteger(MIN_OFFSET_SHIFT_Y, MAX_OFFSET_SHIFT_Y)) / transform.k;
    return { left, top };
}

function randomInteger(min: number, max: number) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}
