import { errorMessageAsString } from "@/utils/simple-error";

export interface SettleFailure<T> {
    item: T;
    error: string;
}

/** Awaits `operation` on each item in order, continuing past failures; returns the failures. */
export async function settleEach<T>(
    items: readonly T[],
    operation: (item: T) => Promise<unknown>,
): Promise<SettleFailure<T>[]> {
    const failures: SettleFailure<T>[] = [];
    for (const item of [...items]) {
        try {
            await operation(item);
        } catch (error) {
            failures.push({ item, error: errorMessageAsString(error) });
        }
    }
    return failures;
}

/** Formats failures as `'name' (error), ...` for a toast or status message. */
export function describeFailures<T>(failures: SettleFailure<T>[], nameOf: (item: T) => string): string {
    return failures.map(({ item, error }) => `'${nameOf(item)}' (${error})`).join(", ");
}
