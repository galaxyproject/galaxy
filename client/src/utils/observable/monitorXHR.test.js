import { matchRoutes, monitorXHR } from "./monitorXHR";

describe("monitorXhr", () => {
    describe("monitorXHR", () => {
        it("should import", () => {
            expect(monitorXHR).toBeInstanceOf(Function);
        });
    });

    // request matcher, XHR object emits objects of form { method, url } which get matched to a set
    // of routes of interest

    describe("matchRoutes", () => {
        let matcher;

        beforeEach(() => {
            matcher = matchRoutes({ routes: ["api/foo"] });
        });

        it("matcher should be a function", () => {
            expect(matcher).toBeInstanceOf(Function);
        });

        it("should recognize an exact route", () => {
            const testPacket = { method: "POST", url: "api/foo" };
            expect(matcher(testPacket)).toBe(true);
        });

        it("should recognize a subroute", () => {
            const testPacket = { method: "POST", url: "api/foo/123" };
            expect(matcher(testPacket)).toBe(true);
        });

        it("should recognize a subroute with some query params", () => {
            const testPacket = { method: "POST", url: "api/foo/123?foo=bar" };
            expect(matcher(testPacket)).toBe(true);
        });

        it("should not match unwatched urls", () => {
            const testPacket = { method: "POST", url: "api/notinthelist" };
            expect(matcher(testPacket)).toBe(false);
        });

        it("should not match unwatched methods", () => {
            const testPacket = { method: "GET", url: "api/notinthelist" };
            expect(matcher(testPacket)).toBe(false);
        });
    });

    describe("matchRoutes: general regex", () => {
        it("should match foo or bar", () => {
            const matcher = matchRoutes({
                routes: [/api\/(foo|bar)/gi],
            });

            const fooTest = { method: "POST", url: "api/foo/asdfasdf" };
            expect(matcher(fooTest)).toBe(true);
            const barTest = { method: "POST", url: "api/bar/asdfasdf" };
            expect(matcher(barTest)).toBe(true);
            const blechTest = { method: "POST", url: "api/blech/asdfasdf" };
            expect(matcher(blechTest)).toBe(false);
        });
    });

    describe("matchRoutes: excludes", () => {
        const matcher = matchRoutes({
            routes: ["api/histories"],
            exclude: ["api/histories/ABC"],
        });

        // should exclude urls containing the restricted ID
        it("should exclude history routes with id=ABC", () => {
            const testRoute = { method: "POST", url: "api/histories/ABC" };
            expect(matcher(testRoute)).toBe(false);
            const testRouteWithParams = { method: "POST", url: "api/histories/ABC?hoohah=123" };
            expect(matcher(testRouteWithParams)).toBe(false);
        });

        // should pass similar routes with different ids
        it("should match other history routes", () => {
            const testRoute = { method: "POST", url: "api/histories/DEF" };
            expect(matcher(testRoute)).toBe(true);
            const testRouteWithParams = { method: "POST", url: "api/histories/DEF?foo=sadfasd" };
            expect(matcher(testRouteWithParams)).toBe(true);
        });
    });
});
