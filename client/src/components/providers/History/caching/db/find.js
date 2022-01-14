import { pipe } from "rxjs";
import { mergeMap } from "rxjs/operators";
import { show, needs } from "utils/observable";

/**
 * Pouchdb-find as an operator
 * https://pouchdb.com/guides/mango-queries.html
 *
 * @param {Observable} db$ Observable pouchDb instance
 */
export const find = (db$, cfg = {}) => {
    const { label = "find", debug = false } = cfg;

    return pipe(
        show(debug, (request) => console.log(`${label} -> request`, request)),
        needs(db$),
        mergeMap(async (inputs) => {
            const [request, db] = inputs;

            const { index } = request;
            if (index !== undefined) {
                const indexResponse = await db.createIndex({ index });
                const { result: idxResult } = indexResponse;
                if (idxResult !== "created" && idxResult !== "exists") {
                    throw new Error("Unknown index creation result", indexResponse);
                }
            }

            let docs;
            try {
                const findResponse = await db.find(request);
                docs = findResponse.docs || [];
            } catch (err) {
                console.warn("find() error", err, request, db.name);
                throw err;
            }

            return docs;
        }),
        show(debug, (result) => console.log(`${label} -> result`, result))
    );
};
