import { of } from "rxjs";
import { map } from "rxjs/operators";
import { aggregateCacheUpdates } from "../ContentProvider";
import { monitorCollectionContent } from "components/providers/History/caching";
import { SEEK } from "components/providers/History/caching/enums";
import { SearchParams } from "components/providers/History/SearchParams";
// import { show } from "utils/observable";

// prettier-ignore
export const watchCollection = (cfg = {}) => elementIndex$ => {
    const { 
        dsc, 
        filters = new SearchParams(),
        pageSize = SearchParams.pageSize, 
        debug = false,
        keyField = "element_index",
        keyDirection = SEEK.ASC,
        ...otherConfig 
    } = cfg;

    // builds a monitor observable based on a element_index
    const monitor = (idx) => of([dsc.contents_url, filters, idx]).pipe(
        monitorCollectionContent({ pageSize, debug: false, keyField }),
    );
    
    // handles the plumbing for observing the query (monitor) and collecting the output into an
    // aggregate ordered list focused around the current target key (element_index in this case)
    return elementIndex$.pipe(
        map(val => parseInt(val)),
        aggregateCacheUpdates(monitor, {
            keyField,
            keyDirection,
            pageSize, 
            debug,
            ...otherConfig,
        }),
    );
};
