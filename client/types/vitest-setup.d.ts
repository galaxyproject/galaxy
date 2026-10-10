import "vitest";

// Custom matchers from tests/vitest/helpers.js
interface CustomMatchers<R = unknown> {
    toBeLocalized(): R;
    toBeLocalizationOf(str: string): R;
}

// Empty interfaces merge the custom matchers into vitest's own types; the type
// parameter must match vitest's declaration exactly.
/* eslint-disable @typescript-eslint/no-empty-object-type, @typescript-eslint/no-explicit-any */
declare module "vitest" {
    interface Assertion<T = any> extends CustomMatchers<T> {}
    interface AsymmetricMatchersContaining extends CustomMatchers {}
}
