/// <reference types="vitest" />
/// <reference types="@testing-library/jest-dom" />

interface CustomMatchers<R = unknown> {
    toBeLocalized(): R;
    toBeLocalizationOf(str: string): R;
}

declare module "vitest" {
    interface Assertion<T = any> extends CustomMatchers<T> {}
    interface AsymmetricMatchersContaining extends CustomMatchers {}
}

// Also extend jest-dom matchers for compatibility
declare global {
    namespace Vi {
        interface JestMatchers<T = any> extends CustomMatchers<T> {}
    }
}
