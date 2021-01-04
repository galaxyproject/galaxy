import { pipe } from "rxjs";
import { map } from "rxjs/operators";

/**
 * Bust incoming numeric source values into blocks of designated size.
 *
 * @param {*} chunkSize
 * @param {*} ceil
 */
// prettier-ignore
export const chunk = (chunkSize, ceil = false) => pipe(
    map((chunkMe) => {
        const rawVal = chunkMe / chunkSize;
        return chunkSize * (ceil ? Math.ceil(rawVal) : Math.floor(rawVal));
    })
);

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
export const chunkParam = (pos, chunkSize, ceil = false) => pipe(
    map((inputs) => {
        const chunkMe = inputs[pos];
        const rawVal = 1.0 * chunkMe / chunkSize;
        const chunkedVal = chunkSize * (ceil ? Math.ceil(rawVal) : Math.floor(rawVal));
        const newInputs = inputs.slice();
        newInputs[pos] = chunkedVal;
        return newInputs;
    })
);
