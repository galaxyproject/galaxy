import { map } from "rxjs/operators";

/**
 * Bust incoming numeric source values into blocks of designated size.
 *
 * @param {Number|Object} cfg object or numeric chunksize
 * @param {*} ceil
 */
// prettier-ignore
export const chunk = (cfg) => {
    const settings = Number.isInteger(cfg) ? { chunkSize: Math.round(cfg) } : cfg;
    const { chunkSize = 0, ceil = false, debug = false, label } = settings;
    if (chunkSize == 0) {
        throw new Error("Please provide a chunk size");
    }

    return map((chunkMe) => {
        const rawVal = 1.0 * chunkMe / chunkSize;
        const result = chunkSize * (ceil ? Math.ceil(rawVal) : Math.floor(rawVal));
        if (debug) {
            console.log(`chunk: ${label}`, chunkMe, result, settings);
        }
        return result;
    })
};

/**
 * Change one parameter to be an multiple of indicated block size. Used to
 * regulate the URLs we send to the server so that some will be cached. Pos is
 * the position in the combined inputs array, and the chunkSize is the size of
 * the block to break the value into.
 *
 * Ex: Source Inputs [ x, y, z, 750 ],
 *     chunkParam(3, 200)
 *     Results in [ x, y, z, 600]
 *
 * @param {integer} pos Input array parameter number to chunk
 * @param {integer} chunkSize Size of chunks
 * @param {Boolean} ceil Math.ceil or Math.floor chunk value
 */
// prettier-ignore
export const chunkParam = (pos, chunkSize, ceil = false) => {
    return map((inputs) => {
        const chunkMe = inputs[pos];
        const rawVal = 1.0 * chunkMe / chunkSize;
        const chunkedVal = chunkSize * (ceil ? Math.ceil(rawVal) : Math.floor(rawVal));
        const newInputs = inputs.slice();
        newInputs[pos] = chunkedVal;
        return newInputs;
    })
}

export const chunkProp = (propName, chunkSize, ceil = false) => {
    return map((obj) => {
        const chunkMe = obj[propName];
        const rawVal = (1.0 * chunkMe) / chunkSize;
        const chunkedVal = chunkSize * (ceil ? Math.ceil(rawVal) : Math.floor(rawVal));
        return { ...obj, [propName]: chunkedVal };
    });
};
