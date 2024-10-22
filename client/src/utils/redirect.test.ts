import { getAppRoot } from "@/onload/loadConfig";

import { withPrefix } from "./redirect";

jest.mock("@/onload/loadConfig");

test("route prefix changes", async () => {
    jest.mocked(getAppRoot).mockReturnValue("/prefix");
    // test routes
    expect(withPrefix("http://")).toEqual("http://");
    expect(withPrefix("/")).toEqual("/prefix/");
    expect(withPrefix("/home")).toEqual("/prefix/home");
    // keep protocols in query parameters intact
    expect(withPrefix("/authz/cilogon/login?idphint=https://test.com")).toEqual(
        "/prefix/authz/cilogon/login?idphint=https://test.com"
    );
    // ensure that it can only be called once
    expect(withPrefix(withPrefix("/home"))).toEqual("/prefix/prefix/home");
    // This doesn't do what it looks like it should do?
});
