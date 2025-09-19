import { getFullAppUrl } from "./utils";

describe("test app utils", () => {
    describe("test getFullAppUrl", () => {
        it("should return the full app url", () => {
            const appUrl = getFullAppUrl();
            expect(appUrl).toBe("http://localhost/");
        });

        it("should return the full app url", () => {
            const appUrl = getFullAppUrl("home");
            expect(appUrl).toBe("http://localhost/home");
        });
    });
});
