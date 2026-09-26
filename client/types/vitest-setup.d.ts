import "vitest";

// Custom matchers from tests/vitest/helpers.js
interface CustomMatchers<R = unknown> {
    toBeLocalized(): R;
    toBeLocalizationOf(str: string): R;
}

declare module "vitest" {
    // Export vitest functions for explicit imports (non-globals mode)
    export const describe: (typeof import("vitest/dist/index.js"))["describe"];
    export const it: (typeof import("vitest/dist/index.js"))["it"];
    export const test: (typeof import("vitest/dist/index.js"))["test"];
    export const expect: (typeof import("vitest/dist/index.js"))["expect"];
    export const vi: (typeof import("vitest/dist/index.js"))["vi"];
    export const beforeEach: (typeof import("vitest/dist/index.js"))["beforeEach"];
    export const afterEach: (typeof import("vitest/dist/index.js"))["afterEach"];
    export const beforeAll: (typeof import("vitest/dist/index.js"))["beforeAll"];
    export const afterAll: (typeof import("vitest/dist/index.js"))["afterAll"];

    // Custom matcher type augmentations for Vitest 4.x
    interface Assertion<T = any> extends CustomMatchers<T> {}
    interface AsymmetricMatchersContaining extends CustomMatchers {}
}
