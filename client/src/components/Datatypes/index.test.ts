import { useServerMock } from "@/api/client/__mocks__";

import { getDatatypesMapper } from "./index";
import { typesAndMappingResponse } from "./test_fixtures";

const { server, http } = useServerMock();

server.use(
    http.get("/api/datatypes/types_and_mapping", ({ response }) => {
        return response(200).json(typesAndMappingResponse);
    })
);

describe("Datatypes/index.js", () => {
    describe("getDatatypesMapper", () => {
        it("should fetch logic from API for comparing datatypes in a hierarchy", async () => {
            await getDatatypesMapper().then((mapper) => {
                expect(mapper.isSubType("txt", "data")).toBe(true);
                expect(mapper.isSubType("txt", "txt")).toBe(true);
                expect(mapper.isSubType("data", "txt")).toBe(false);
                expect(mapper.isSubTypeOfAny("data", ["txt", "data"])).toBe(true);
            });
        });
    });
});
