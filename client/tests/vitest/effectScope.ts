import { onTestFinished } from "vitest";
import { effectScope } from "vue";

/** Runs `fn` (typically a composable) in an effect scope stopped when the current test finishes. */
export function runInTestScope<T>(fn: () => T): T {
    const scope = effectScope();
    onTestFinished(() => scope.stop());
    return scope.run(fn)!;
}
