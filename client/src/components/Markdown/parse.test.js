import { getArgs } from "./parse";

describe("parse.ts", () => {
    describe("getArgs", () => {
        it("parses simple directive expression", () => {
            const args = getArgs("job_metrics(job_id=THISFAKEID)");
            expect(args.name).toBe("job_metrics");
        });
    });
});
