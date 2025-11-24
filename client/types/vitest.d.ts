declare module "vitest" {
    export const describe: (typeof import("vitest/dist/index.js"))["describe"];
    export const it: (typeof import("vitest/dist/index.js"))["it"];
    export const test: (typeof import("vitest/dist/index.js"))["test"];
    export const expect: (typeof import("vitest/dist/index.js"))["expect"];
    export const vi: (typeof import("vitest/dist/index.js"))["vi"];
    export const beforeEach: (typeof import("vitest/dist/index.js"))["beforeEach"];
    export const afterEach: (typeof import("vitest/dist/index.js"))["afterEach"];
    export const beforeAll: (typeof import("vitest/dist/index.js"))["beforeAll"];
    export const afterAll: (typeof import("vitest/dist/index.js"))["afterAll"];
}
