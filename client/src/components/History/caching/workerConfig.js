/**
 * Configuration var for inside the worker, must be set when worker
 * is fired up because we can't reach the document and that's how stupid,
 * stupid, stupid, stupid, galaxy backbone code gets some of its config.
 */
export const workerConfig = { root: "/" };

export const configure = (options = {}) => {
    Object.assign(workerConfig, options);
};

/**
 * Prepend against this config. Can't access document so we can't use
 * the standard one from utils
 */
const slashCleanup = /(\/)+/g;
export function prependPath(path) {
    const root = workerConfig.root;
    return `${root}/${path}`.replace(slashCleanup, "/");
}
