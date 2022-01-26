import axios from "axios";
import { snakeCase } from "snake-case";

export function invocationsProvider(ctx, callback, extraParams) {
    const { apiUrl, ...requestParams } = ctx;
    const cleanParams = {};
    Object.entries(requestParams).map(([key, val]) => {
        if (key === "perPage") {
            key = "limit";
        }
        if (val) {
            cleanParams[snakeCase(key)] = val;
        }
    });
    if (cleanParams.current_page && cleanParams.limit) {
        cleanParams.offset = (cleanParams.current_page - 1) * cleanParams.limit;
        delete cleanParams.current_page;
    }
    const promise = axios.get(apiUrl, { params: { ...cleanParams, ...extraParams } });

    // Must return a promise that resolves to an array of items
    return promise.then((data) => {
        // Pluck the array of items off our axios response
        const items = data.data;
        callback && callback(data);
        // Must return an array of items or an empty array if an error occurred
        return items || [];
    });
}
