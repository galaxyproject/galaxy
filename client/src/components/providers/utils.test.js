// sanity check tests for providers utils

import { cleanPaginationParameters } from "./utils";

describe("Providers utils", () => {
    test("Clean Pagination Parameters", () => {
        let requestParams = {
            perPage: 1,
            current_page: 1,
        };
        let cleanParams = cleanPaginationParameters(requestParams);
        expect(cleanParams).toEqual({
            limit: 1,
            offset: 0,
        });
        requestParams = {
            perPage: 1,
            current_page: 2,
            randomParam: "randomValue",
        };
        cleanParams = cleanPaginationParameters(requestParams);
        expect(cleanParams).toEqual({
            limit: 1,
            offset: 1,
            random_param: "randomValue",
        });
        requestParams = {
            offset: 3,
        };
        cleanParams = cleanPaginationParameters(requestParams);
        expect(cleanParams).toEqual({
            offset: 3,
        });
    });
});
