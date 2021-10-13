/**
 * Houses linear regression and polynomial fitting methods in the API of
 * a Map. Set values to insert data points, Get other x values to return
 * approximations (or the actual datapoints if they exist)
 */

import { linear, polynomial } from "regression";
import { map, pipe, filter, windowAhead } from "iter-tools";

class CurveFitInputError extends Error {}
class CurveFitSampleError extends Error {}

const xAscending = ([xa], [xb]) => xa - xb;
const isDefined = filter((pt) => pt !== undefined);

export class CurveFit extends Map {
    constructor(data) {
        super(data);
        this._domain = [-Infinity, Infinity];
        this.xPrecision = 0;
        this.yPrecision = 0;
    }

    // cast keys and vals as numbers
    set(key, val) {
        const x = this.round(key, this.xPrecision);
        const y = this.round(val, this.yPrecision);
        if (isFinite(x) && isFinite(y) && val !== undefined && val !== null && this.valInDomain(x)) {
            super.set(x, y);
        }
    }

    get(key, opts = {}) {
        if (isNaN(key)) {
            const errMsg = "Please provide a numeric input";
            throw new CurveFitInputError(errMsg);
        }

        const { interpolate = false, order = 2, precision = this.yPrecision } = opts;
        const x = this.round(key, this.xPrecision);
        const inDomain = this.valInDomain(x);

        let result = undefined;
        if (inDomain) {
            if (this.has(x)) {
                result = super.get(x);
            } else {
                const method = interpolate ? this.linearInterpolate : this.curveFit;
                result = method.call(this, x, { order, precision });
            }
        }

        return result;
    }

    get hasData() {
        return this.size >= 2;
    }

    get dataPoints() {
        return Array.from(this.entries()).sort(xAscending);
    }

    get domain() {
        return this._domain;
    }

    set domain(newDomain) {
        this.pruneDomain(newDomain);
        this._domain = newDomain;
    }

    // fancier round function, has precision option so we can round to the
    // nearest indicated power of 10
    round(n, precision) {
        const factor = 10 ** precision;
        return Math.round(+n * factor) / factor;
    }

    pruneDomain(domain) {
        const notInDomain = (val) => !this.valInDomain(val, domain);
        const doomed = filter(notInDomain, this.keys());
        for (const x of doomed) {
            this.delete(x);
        }
    }

    valInDomain(x, domain = this.domain) {
        const [bottom, top] = domain;
        return x >= bottom && x <= top;
    }

    pointInDomain([x], domain = this.domain) {
        return this.valInDomain(x, domain);
    }

    curveFit(x, opts = {}) {
        if (this.size < 2) {
            const errMsg = "Need at least 2 points to perform an approximation";
            throw new CurveFitSampleError(errMsg);
        }
        const approxMethod = this.size == 2 ? linear : polynomial;
        const { predict } = approxMethod(this.dataPoints, opts);
        const [, y] = predict(x);
        return y;
    }

    // finds closest two data points and does a linear interpolation between
    // them at the provided x value
    linearInterpolate(x, opts = {}) {
        const fn = this.getPointWiseFilter(x);
        const [bookends] = Array.from(fn(this.dataPoints));
        if (bookends && bookends.length) {
            const { predict } = linear(bookends, opts);
            const [, y] = predict(x);
            return y;
        }
        return undefined;
    }

    // finds the data points to the left and right of indicated xval
    getPointWiseFilter(x) {
        return pipe(
            windowAhead(2),
            map((w) => Array.from(isDefined(w))),
            filter((pts) => {
                if (pts.length == 2) {
                    const [[x1], [x2]] = pts;
                    return x > x1 && x < x2;
                }
                return false;
            })
        );
    }

    clone() {
        const newFit = new CurveFit();
        newFit.xPrecision = this.xPrecision;
        newFit.yPrecision = this.yPrecision;
        newFit.domain = this.domain;
        for (const [x, y] of this.entries()) {
            newFit.set(x, y);
        }
        return newFit;
    }
}
