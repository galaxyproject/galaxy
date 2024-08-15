import { fetchDatatypesAndMappings } from "@/api/datatypes";

import { getDatatypesMapper } from "./index";
import { typesAndMappingResponse } from "./test_fixtures";

jest.mock("@/api/datatypes");

describe("Datatypes/index.js", () => {
    describe("getDatatypesMapper", () => {
        it("should fetch logic from API for comparing datatypes in a hierarchy", async () => {
            fetchDatatypesAndMappings.mockResolvedValue(typesAndMappingResponse);
            await getDatatypesMapper().then((mapper) => {
                expect(mapper.isSubType("txt", "data")).toBe(true);
                expect(mapper.isSubType("txt", "txt")).toBe(true);
                expect(mapper.isSubType("data", "txt")).toBe(false);
                expect(mapper.isSubTypeOfAny("data", ["txt", "data"])).toBe(true);
            });
        });
    });
});
