/**
 * Raised by a provider whose scope could not be loaded at all — the very first
 * fetch of an empty cache failed, so there is nothing to render and "No
 * results." would be a lie.
 *
 * Every other failure stays quiet: once a store holds rows, a failing search or
 * background refresh still leaves the cached ones on screen, which is a better
 * answer than an error.
 */
export class PaletteFetchError extends Error {
    constructor(cause?: unknown) {
        super("The command palette could not load this scope");
        this.name = "PaletteFetchError";
        this.cause = cause;
    }
}

export function isPaletteFetchError(error: unknown): error is PaletteFetchError {
    return error instanceof PaletteFetchError;
}

/**
 * Runs the fetch that fills an empty cache, reporting a failure instead of
 * swallowing it — see {@link PaletteFetchError}.
 */
export async function fetchOrFail(fetch: () => Promise<unknown>): Promise<void> {
    try {
        await fetch();
    } catch (error) {
        throw new PaletteFetchError(error);
    }
}
