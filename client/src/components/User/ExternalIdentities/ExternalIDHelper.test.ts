import { describe, expect, it } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import { submitCILogon } from "./ExternalIDHelper";

const { server, http } = useServerMock();

describe("submitCILogon", () => {
    it("sends the post-login destination", async () => {
        let next: FormDataEntryValue | null = null;
        server.use(
            http.untyped.post(/.*\/authnz\/cilogon\/login.*/, async ({ request }) => {
                next = (await request.formData()).get("next");
                return HttpResponse.json({ redirect_uri: "https://cilogon.example/authorize" });
            }),
        );
        const redirectUri = await submitCILogon(true, "urn:idp", "https://tools.example.org/back");
        expect(redirectUri).toBe("https://cilogon.example/authorize");
        expect(next).toBe("https://tools.example.org/back");
    });
});
