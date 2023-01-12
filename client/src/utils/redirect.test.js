import { withPrefix } from "./redirect";
import { getAppRoot } from "onload/loadConfig";

jest.mock("onload/loadConfig");
getAppRoot.mockImplementation(() => "/prefix");

describe("test path handling", () => {
    it("route prefix changes", async () => {
        // test routes
        expect(withPrefix()).toEqual(undefined);
        expect(withPrefix("http://")).toEqual("http://");
        expect(withPrefix("/")).toEqual("/prefix/");
        expect(withPrefix("/home")).toEqual("/prefix/home");
        // ensure that it can only be called once
        expect(withPrefix(withPrefix("/home"))).toEqual("/prefix/prefix/home");
    });
});
