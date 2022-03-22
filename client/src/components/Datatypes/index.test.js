import axios from "axios";
import MockAdapter from "axios-mock-adapter";

import { getDatatypesMapper } from "./index";
import { typesAndMappingResponse } from "./test_fixtures";

describe("Datatypes/index.js", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = new MockAdapter(axios);
    });

    afterEach(() => {
        axiosMock.restore();
    });

    describe("getDatatypesMapper", () => {
        it("should fetch logic from API for comparing datatypes in a hierarchy", async () => {
            axiosMock.onGet(`/api/datatypes/types_and_mapping`).reply(200, typesAndMappingResponse);
            await getDatatypesMapper().then((mapper) => {
                expect(mapper.isSubType("txt", "data")).toBe(true);
                expect(mapper.isSubType("txt", "txt")).toBe(true);
                expect(mapper.isSubType("data", "txt")).toBe(false);
                expect(mapper.isSubTypeOfAny("data", ["txt", "data"])).toBe(true);
            });
        });
    });
});
