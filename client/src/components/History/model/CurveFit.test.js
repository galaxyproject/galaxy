import { CurveFit } from "./CurveFit";

describe("CurveFit utility", () => {
    describe("size prop", () => {
        test("should be a map with a size prop", () => {
            const fit = new CurveFit();
            expect(fit.size).toBe(0);
        });

        test("can accept new data points", () => {
            const fit = new CurveFit();
            fit.set(0, 0);
            fit.set(100, 100);
            expect(fit.size).toBe(2);
            expect(fit.dataPoints.length).toEqual(2);
        });

        test("converts all inputs to numeric values", () => {
            const fit = new CurveFit();
            fit.set("0", 0);
            fit.set("100", "100");
            expect(fit.dataPoints.length).toEqual(2);
            expect(fit.dataPoints).toEqual([
                [0, 0],
                [100, 100],
            ]);
        });
    });

    describe("dataPoints prop", () => {
        test("has a data property which is an array of arrays", () => {
            const fit = new CurveFit();
            fit.set(100, 100);
            fit.set(20, 3000);
            fit.set(0, 0);
            expect(fit.dataPoints).toEqual([
                [0, 0],
                [20, 3000],
                [100, 100],
            ]);
        });
    });

    describe("xPrecision & yPrecision", () => {
        test("integers (precision = 0)", () => {
            const fit = new CurveFit();
            fit.xPrecision = 0;
            fit.yPrecision = 0;
            fit.set(100.234234, 100.234234);
            fit.set(20.2342342342, 3000.2342342342);
            fit.set(0.000003, 0.000002);

            expect(fit.dataPoints).toEqual([
                [0, 0],
                [20, 3000],
                [100, 100],
            ]);
        });

        test("positive precision", () => {
            const fit = new CurveFit();
            fit.xPrecision = 1;
            fit.yPrecision = 2;
            fit.set(100.234234, 100.234234);
            fit.set(20.2342342342, 3000.2342342342);
            fit.set(0.000003, 0.000002);

            expect(fit.dataPoints).toEqual([
                [0, 0],
                [20.2, 3000.23],
                [100.2, 100.23],
            ]);
        });

        test("negative precision", () => {
            const fit = new CurveFit();
            fit.xPrecision = -1;
            fit.yPrecision = -2;
            fit.set(111.234234, 22222.234234);
            fit.set(20.2342342342, 3333.2342342342);
            fit.set(2.11111111, 40.2222222);

            expect(fit.dataPoints).toEqual([
                [0, 0],
                [20, 3300],
                [110, 22200],
            ]);
        });
    });

    describe("fit a 2 point line", () => {
        // given (0,0), (100,300), expect (50,150)
        test("find the middle of a line when the data set is only 2 points", () => {
            const fit = new CurveFit();
            fit.set(100, 300);
            fit.set(0, 0);

            expect(fit.get(0)).toBe(0);
            expect(fit.get(100)).toBe(300);
            expect(fit.get(50)).toBe(150);
        });
    });

    describe("fit a point on simple curves", () => {
        test("y = x^2", () => {
            const fit = new CurveFit();
            fit.set(0, 0);
            fit.set(2, 4);
            fit.set(3, 9);

            expect(fit.get(4, { order: 2 })).toEqual(16);
            expect(fit.get(4, { order: 3 })).toEqual(16);
            expect(fit.get(4, { order: 4 })).toEqual(16);
        });

        test("y = x^3", () => {
            const fit = new CurveFit();
            fit.set(0, 0);
            fit.set(1, 1);
            fit.set(2, 8);
            fit.set(3, 27);

            expect(fit.get(4, { order: 3 })).toEqual(64);
        });

        test("approximation should be in the ballpark", () => {
            const fit = new CurveFit();
            fit.set(0, 0);
            fit.set(1, 1);
            fit.set(2, 8);
            fit.set(3, 27);

            // approximate with only 2 terms, but w know it's really a cubic,
            // should be off but in the ballpark
            const approx = fit.get(4, { order: 2 });
            expect(approx).toBeGreaterThan(Math.pow(3, 3));
            expect(approx).toBeLessThan(Math.pow(5, 3));
        });
    });

    describe("domain prop", () => {
        let fit;
        beforeEach(() => {
            fit = new CurveFit();
            fit.domain = [0, 2];
            fit.set(0, 0);
            fit.set(1, 1);
            fit.set(2, 8);
            fit.set(3, 1000000000);
        });

        test("resetting domain removes datapoints outside of new domain", () => {
            fit.domain = [0, 1];
            expect(fit.dataPoints).toEqual([
                [0, 0],
                [1, 1],
            ]);
        });

        test("can restrict evaluated datapoints based on a set domain of inputs", () => {
            expect(fit.dataPoints).toEqual([
                [0, 0],
                [1, 1],
                [2, 8],
            ]);
        });

        test("appoximations will ignore datapoints outside domain", () => {
            expect(fit.get(3, { order: 3 })).toBe(undefined);
            fit.domain = [0, 3];
            expect(fit.get(3, { order: 3 })).toBe(27);
        });
    });

    // estimates value by drawing a line between the two closest points and
    // doing a linear approx
    describe("linear pointwise interpolation", () => {
        let fit;
        beforeEach(() => {
            fit = new CurveFit();
            fit.xPrecision = 1;
            fit.domain = [0, 3];
            fit.set(0.0, 0);
            fit.set(1.0, 1);
            fit.set(2.0, 8);
            fit.set(3.0, 32);
        });

        test("2.5 -> 20", () => {
            expect(fit.linearInterpolate(2.5)).toEqual(20);
            expect(fit.get(2.5, { interpolate: true })).toEqual(20);
        });
    });

    describe("clone", () => {
        let fit;
        beforeEach(() => {
            fit = new CurveFit();
            fit.xPrecision = 1;
            fit.domain = [0, 3];
            fit.set(0.0, 0);
            fit.set(1.0, 1);
            fit.set(2.0, 8);
        });

        test("clone, hope for same data", () => {
            const existingData = fit.dataPoints;
            const newMap = fit.clone();
            const cloneData = newMap.dataPoints;
            expect(existingData).toEqual(cloneData);
        });
    });
});
