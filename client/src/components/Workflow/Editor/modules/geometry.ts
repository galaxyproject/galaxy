/** simple rectangle without rotation */
export interface Rectangle {
    x: number;
    y: number;
    width: number;
    height: number;
}

/**
 * Class compatible with rectangle interface.
 * Provides additional properties and methods specific to bounding boxes.
 * Useful to calculate the bounds of multiple rectangles,
 * using the `fitRectangle` method.
 */
export class AxisAlignedBoundingBox implements Rectangle {
    /** x coordinate of left edge */
    x = Infinity;

    /** y coordinate of upper edge */
    y = Infinity;

    /** x coordinate of right edge */
    endX = -Infinity;

    /** y coordinate of lower edge */
    endY = -Infinity;

    get width() {
        const width = this.endX - this.x;
        return width > 0 ? width : 0;
    }

    set width(value) {
        this.endX = this.x + value;
    }

    get height() {
        const height = this.endY - this.y;
        return height > 0 ? height : 0;
    }

    set height(value) {
        this.endY = this.y + value;
    }

    reset() {
        this.x = Infinity;
        this.y = Infinity;
        this.endX = -Infinity;
        this.endY = -Infinity;
    }

    /** expand bounding box to fit a rectangle */
    fitRectangle(rect: Readonly<Rectangle>) {
        if (this.x > rect.x) {
            this.x = rect.x;
        }

        if (this.y > rect.y) {
            this.y = rect.y;
        }

        if (this.endX < rect.x + rect.width) {
            this.endX = rect.x + rect.width;
        }

        if (this.endY < rect.y + rect.height) {
            this.endY = rect.y + rect.height;
        }
    }

    /** make width and height the same, maintaining the center of the bounding box */
    squareCenter() {
        if (this.width > this.height) {
            const difference = this.width - this.height;
            this.y -= difference * 0.5;
            this.endY += difference * 0.5;
        } else {
            const difference = this.height - this.width;
            this.x -= difference * 0.5;
            this.endX += difference * 0.5;
        }
    }

    /** expand bounding box in every direction */
    expand(by: number) {
        this.x -= by;
        this.y -= by;
        this.endX += by;
        this.endY += by;
    }

    /** check if a point is inside the bounding box */
    isPointInBounds(point: { x: number; y: number }) {
        if (point.x > this.x && point.y > this.y && point.x < this.endX && point.y < this.endY) {
            return true;
        } else {
            return false;
        }
    }
}

/* Format
   [a b
    c d
    e f]
   as used by canvas: https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/transform
*/
// prettier-ignore
export type Matrix = [
    number, number,
    number, number,
    number, number,
];

/** vector as a tuple */
export type Vector = [number, number];

/**
 * Wraps basic transform operations.
 * Each operation returns a new instance, so method calls can be chained
 * without mutating the initial transform.
 */
export class Transform {
    matrix: Matrix;

    constructor(matrix: Matrix = [1, 0, 0, 1, 0, 0]) {
        this.matrix = matrix;
    }

    /** returns a new transform with a translation vector added */
    translate(vector: Vector) {
        // prettier-ignore
        return new Transform([
            this.matrix[0], this.matrix[1],
            this.matrix[2], this.matrix[3],
            this.matrix[4] + vector[0], this.matrix[5] + vector[1]
        ]);
    }

    /** returns a new transform scaled by a given vector */
    scale(vector: Vector) {
        // prettier-ignore
        return new Transform([
            this.matrix[0] * vector[0], this.matrix[1] * vector[1],
            this.matrix[2] * vector[0], this.matrix[3] * vector[1],
            this.matrix[4], this.matrix[5]
        ]);
    }

    /** Returns the inverse vector. Can be used to un-transform things */
    inverse() {
        const m = this.matrix;
        // https://www.wolframalpha.com/input?i=Inverse+%5B%7B%7Ba%2Cc%2Ce%7D%2C%7Bb%2Cd%2Cf%7D%2C%7B0%2C0%2C1%7D%7D%5D
        const denominator = m[0] * m[3] - m[1] * m[2];

        const a = m[3] / denominator;
        const b = m[1] / -denominator;
        const c = m[2] / -denominator;
        const d = m[0] / denominator;
        const e = (m[3] * m[4] - m[2] * m[5]) / -denominator;
        const f = (m[1] * m[4] - m[0] * m[5]) / denominator;

        // prettier-ignore
        return new Transform([
            a, b,
            c, d,
            e, f
        ]);
    }

    /** applies this transform to a rendering context */
    applyToContext(ctx: CanvasRenderingContext2D): void {
        ctx.transform(...this.matrix);
    }

    /** returns a vector transformed by this transform */
    apply(vector: Vector): Vector {
        return [
            this.matrix[0] * vector[0] + this.matrix[2] * vector[1] + this.matrix[4],
            this.matrix[1] * vector[0] + this.matrix[3] * vector[1] + this.matrix[5],
        ];
    }

    /** removes the translation portion of the transform */
    resetTranslation(): Transform {
        // prettier-ignore
        return new Transform ([
            this.matrix[0], this.matrix[1],
            this.matrix[2], this.matrix[3],
            0, 0
        ]);
    }

    get scaleX() {
        return this.matrix[0];
    }

    get scaleY() {
        return this.matrix[3];
    }
}
