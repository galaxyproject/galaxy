import { LastQueue } from "./promise-queue";
const x = 10;
const lastQueue = new LastQueue(x);

async function testPromise(args) {
    return new Promise((resolve) => resolve(args));
}

describe("test last-queue", () => {
    it("should only resolve the first and last promise", async () => {
        const results = [];
        for (let i = 0; i < x; i++) {
            lastQueue.enqueue(testPromise, i).then((response) => {
                results.push(response);
            });
        }
        await lastQueue.enqueue(testPromise, x).then((response) => {
            results.push(response);
        });
        expect(results).toEqual([0, x]);
    });

    it("should only resolve the last promise for each key", async () => {
        const results = [];
        for (let i = 0; i < x; i++) {
            for (let j = 0; j < x; j++) {
                lastQueue.enqueue(testPromise, i, i).then((response) => {
                    results.push(response);
                });
            }
        }
        await lastQueue.enqueue(testPromise, x, x).then((response) => {
            results.push(response);
        });
        expect(results).toEqual([...Array(x + 1).keys()]);
    });
});
