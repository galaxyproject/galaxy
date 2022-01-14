// common mock implementation
// having a hard time making jest manually mock this properly

import { map } from "rxjs/operators";
import { getPropRange } from "components/providers/History/caching/loadHistoryContents";
import { serverContent } from "components/providers/History/test/testHistory";

export const loadContents = jest.fn().mockImplementation((config) => {
    const { filters } = config;

    return map((pagination) => {
        const { offset, limit } = pagination;

        // server side result set
        const searchResults = serverContent(filters);
        const { min: minHid, max: maxHid } = getPropRange(searchResults, "hid");

        // window slice returned
        const result = searchResults.slice(offset, offset + limit);
        const { min: minContentHid, max: maxContentHid } = getPropRange(result, "hid");

        return {
            summary: {},
            matches: result.length,
            totalMatches: searchResults.length,
            minHid,
            maxHid,
            minContentHid,
            maxContentHid,
            limit,
            offset,
        };
    });
});
