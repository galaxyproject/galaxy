import { type HistoryDetailed, type HistorySummary, type MessageException } from "@/api";
import { GalaxyApi } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";

const TEST_HISTORY_SUMMARY: HistorySummary = {
    model_class: "History",
    id: "test",
    name: "Test History",
    archived: false,
    deleted: false,
    purged: false,
    published: false,
    update_time: "2021-09-01T00:00:00",
    count: 0,
    annotation: "Test History Annotation",
    tags: [],
    url: "/api/histories/test",
};

const TEST_HISTORY_DETAILED: HistoryDetailed = {
    ...TEST_HISTORY_SUMMARY,
    create_time: "2021-09-01T00:00:00",
    contents_url: "/api/histories/test/contents",
    importable: false,
    slug: "testSlug",
    size: 0,
    user_id: "userID",
    username_and_slug: "username/slug",
    state: "ok",
    empty: true,
    hid_counter: 0,
    genome_build: null,
    state_ids: {},
    state_details: {},
};

const EXPECTED_500_ERROR: MessageException = { err_code: 500, err_msg: "Internal Server Error" };

// Mock the server responses
const { server, http } = useServerMock();
server.use(
    http.get("/api/histories/{history_id}", ({ params, query, response }) => {
        if (query.get("view") === "detailed") {
            return response(200).json(TEST_HISTORY_DETAILED);
        }
        if (params.history_id === "must-fail") {
            return response("5XX").json(EXPECTED_500_ERROR, { status: 500 });
        }
        return response(200).json(TEST_HISTORY_SUMMARY);
    })
);

describe("useServerMock", () => {
    it("mocks the Galaxy Server", async () => {
        {
            const { data, error } = await GalaxyApi().GET("/api/histories/{history_id}", {
                params: {
                    path: { history_id: "test" },
                    query: { view: "summary" },
                },
            });

            expect(error).toBeUndefined();

            expect(data).toBeDefined();
            expect(data).toEqual(TEST_HISTORY_SUMMARY);
        }

        {
            const { data, error } = await GalaxyApi().GET("/api/histories/{history_id}", {
                params: {
                    path: { history_id: "test" },
                    query: { view: "detailed" },
                },
            });

            expect(error).toBeUndefined();

            expect(data).toBeDefined();
            expect(data).toEqual(TEST_HISTORY_DETAILED);
        }

        {
            const { data, error } = await GalaxyApi().GET("/api/histories/{history_id}", {
                params: {
                    path: { history_id: "must-fail" },
                },
            });

            expect(error).toBeDefined();
            expect(error).toEqual(EXPECTED_500_ERROR);

            expect(data).toBeUndefined();
        }

        {
            const { data, error } = await GalaxyApi().GET("/api/configuration");

            expect(data).toBeUndefined();

            expect(error).toBeDefined();
            expect(`${JSON.stringify(error)}`).toContain(
                "Make sure you have added a request handler for this request in your tests."
            );
        }
    });
});
