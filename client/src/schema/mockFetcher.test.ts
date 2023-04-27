import { mockFetcher } from "./__mocks__/fetcher";
import { fetcher } from "@/schema";

jest.mock("@/schema");

mockFetcher.path("/api/configuration").method("get").mock("CONFIGURATION");

mockFetcher
    .path(/^.*\/histories\/.*$/)
    .method("get")
    .mock("HISTORY");

mockFetcher
    .path(/\{history_id\}/)
    .method("put")
    .mock((param: { history_id: string }) => `param:${param.history_id}`);

describe("mockFetcher", () => {
    it("mocks fetcher", async () => {
        {
            const fetch = fetcher.path("/api/configuration").method("get").create();
            const value = await fetch({});

            expect(value).toEqual("CONFIGURATION");
        }

        {
            const fetch = fetcher.path("/api/histories/deleted").method("get").create();
            const value = await fetch({});

            expect(value).toEqual("HISTORY");
        }

        {
            const fetchHistory = fetcher.path("/api/histories/{history_id}/exports").method("put").create();
            const value = await fetchHistory({ history_id: "test" });

            expect(value).toEqual("param:test");
        }
    });
});
