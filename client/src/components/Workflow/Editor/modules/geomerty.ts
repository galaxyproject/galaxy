export interface Rectangle {
    x: number;
    y: number;
    width: number;
    height: number;
}

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
        return this.endX - this.x;
    }

    set width(value) {
        this.endX = this.x + value;
    }

    get height() {
        return this.endY - this.y;
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
}
