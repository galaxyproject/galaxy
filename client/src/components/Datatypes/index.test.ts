import { describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import { getDatatypesMapper } from "./index";
import { typesAndMappingResponse } from "./test_fixtures";

const { server, http } = useServerMock();

server.use(
    http.get("/api/datatypes/types_and_mapping", ({ response }) => {
        return response(200).json(typesAndMappingResponse);
    }),
);

describe("Datatypes API", () => {
    describe("getDatatypesMapper", () => {
        it("compares datatypes using the hierarchy fetched from the API", async () => {
            const mapper = await getDatatypesMapper();

            expect(mapper.isSubType("txt", "data")).toBe(true);
            expect(mapper.isSubType("txt", "txt")).toBe(true);
            expect(mapper.isSubType("data", "txt")).toBe(false);
            expect(mapper.isSubTypeOfAny("data", ["txt", "data"])).toBe(true);
        });
    });
});
