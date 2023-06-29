import { getDatatypesMapper } from "./index";
import { getDatatypes } from "./services";
import { typesAndMappingResponse } from "./test_fixtures";

jest.mock("./services");

describe("Datatypes/index.js", () => {
    describe("getDatatypesMapper", () => {
        it("should fetch logic from API for comparing datatypes in a hierarchy", async () => {
            getDatatypes.mockResolvedValue(typesAndMappingResponse);
            await getDatatypesMapper().then((mapper) => {
                expect(mapper.isSubType("txt", "data")).toBe(true);
                expect(mapper.isSubType("txt", "txt")).toBe(true);
                expect(mapper.isSubType("data", "txt")).toBe(false);
                expect(mapper.isSubTypeOfAny("data", ["txt", "data"])).toBe(true);
            });
        });
    });
});
