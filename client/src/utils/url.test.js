import { addSearchParams } from "./url";

describe("test url utilities", () => {
    it("adding parameters to url", async () => {
        expect(addSearchParams("/test?name=value")).toBe("/test?name=value");
        expect(addSearchParams("/test", { name: "value", and: "this" })).toBe("/test?name=value&and=this");
        expect(addSearchParams("/test?exists=value", { name: "value" })).toBe("/test?exists=value&name=value");
    });
});
