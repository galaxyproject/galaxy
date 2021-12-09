import { watchForChange } from "jest/helpers";
import { defaultPayload } from "components/providers/History/ContentProvider";

/**
 *  Vue adds a bunch of setters and getters so we need to create our own comparison fn
 */
export const sameVueObj = (a, b) => {
    return JSON.stringify(a) == JSON.stringify(b);
};

/**
 * Detects a new emission of a "payload" a standardized object delivered by HistoryContentProvider
 * and CollectionContentProvider, skips the default value that's emitted when it initialized
 *
 * @param   {Object}  config  vm, propName, label, other watchForChange configs
 * @return  {Promise}         promise that resolves with the changed payload
 */
export const payloadChange = async (config = {}) => {
    const { vm, propName = "payload", label = "payload change", skipDefault = false, ...cfg } = config;
    const result = await watchForChange({ vm, propName, label, ...cfg });

    // can see how fast the response comes back by monitoring this result
    // console.log("payloadChange result", JSON.stringify(result.newVal));
    // chopout the placeholder flag for the default
    // eslint-disable-next-line no-unused-vars
    const { placeholder, ...payload } = result.newVal;
    if (skipDefault && sameVueObj(payload, defaultPayload)) {
        return await payloadChange(config);
    }

    return payload;
};

export const reportPayload = (payload, { indexKey = "hid", label = "payload" } = {}) => {
    const { contents = [], startKeyIndex, ...resultFields } = payload;
    const keys = contents.map((o, idx) => {
        const thisKey = o[indexKey];
        const keyString = idx == startKeyIndex ? `${thisKey}*` : thisKey;
        return keyString;
    });
    const report = { keys, startKeyIndex, ...resultFields };
    console.log(label, report);
};
