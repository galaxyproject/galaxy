import { safePath } from "./redirect";
import { getAppRoot } from "onload/loadConfig";

jest.mock("onload/loadConfig");
getAppRoot.mockImplementation(() => "/prefix");

describe("test path handling", () => {
    it("route prefix changes", async () => {
        // test routes
        expect(safePath()).toEqual(undefined);
        expect(safePath("http://")).toEqual("http://");
        expect(safePath("/")).toEqual("/prefix/");
        expect(safePath("/home")).toEqual("/prefix/home");
        // ensure that it can only be called once
        expect(safePath(safePath("/home"))).toEqual("/prefix/prefix/home");
    });
});
