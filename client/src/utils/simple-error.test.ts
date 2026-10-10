import axios from "axios";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import { errorMessageAsString } from "./simple-error";

const { server } = useServerMock();

async function axiosError(response: Response) {
    server.use(http.get("/api/configuration", () => response));
    try {
        await axios.get("/api/configuration");
    } catch (e) {
        return e;
    }
    expect.unreachable("should have thrown");
}

describe("errorMessageAsString", () => {
    // Browsers leave statusText empty over HTTP/2, and msw's HttpResponse would fill it in.
    it.each([
        [413, "The request was too large (413)"],
        [524, "Galaxy took too long to respond (524)"],
        [418, "The request failed (418)"],
    ])("names a %d from axios without relying on the status text", async (status, message) => {
        const error = await axiosError(new Response("<html><body>nginx</body></html>", { status }));

        expect(errorMessageAsString(error)).toBe(message);
    });

    it("falls back to the status text for a status it has no wording for", async () => {
        const error = await axiosError(new HttpResponse("<html><body>teapot</body></html>", { status: 418 }));

        expect(errorMessageAsString(error)).toBe("I'm a Teapot (418)");
    });

    it("prefers the Galaxy error message in an axios response", async () => {
        const error = await axiosError(
            HttpResponse.json({ err_msg: "Quota exceeded", err_code: 403002 }, { status: 403 }),
        );

        expect(errorMessageAsString(error)).toBe("Quota exceeded");
    });
});
