import type { paths } from "@/schema";

jest.mock("@/schema", () => ({
    fetcher: mockFetcher,
}));

jest.mock("@/schema/fetcher", () => ({
    fetcher: mockFetcher,
}));

type Path = keyof paths;
type Method = "get" | "post" | "put" | "delete";

interface MockValue {
    path: Path | RegExp;
    method: Method;
    value: any;
}

const mockValues: MockValue[] = [];

function getMockReturn(path: Path, method: Method, args: any[]) {
    for (let i = mockValues.length - 1; i >= 0; i--) {
        const matchPath = mockValues[i]!.path;
        const matchMethod = mockValues[i]!.method;
        const value = mockValues[i]!.value;

        const getValue = () => {
            if (typeof value === "function") {
                return value(...args);
            } else {
                return value;
            }
        };

        if (matchMethod !== method) {
            continue;
        }

        if (typeof matchPath === "string") {
            if (matchPath === path) {
                return getValue();
            }
        } else {
            if (path.match(matchPath)) {
                return getValue();
            }
        }
    }

    return null;
}

function setMockReturn(path: Path | RegExp, method: Method, value: any) {
    mockValues.push({
        path,
        method,
        value,
    });
}

/**
 * Mock implementation for the fetcher found in `@/schema/fetcher`
 *
 * You need to call `jest.mock("@/schema")` and/or `jest.mock("@/schema/fetcher")`
 * (depending on what module the file you are testing imported)
 * in order for this mock to take effect.
 *
 * To specify return values for the mock, use
 * `mockFetcher.path(...).method(...).mock(desiredReturnValue)`
 * This will cause any use of fetcher on the same path and method to receive the contents of `desiredReturnValue`.
 *
 * If this return value is a function, it will be ran and passed the parameters passed to the fetcher, and it's result returned.
 *
 * `path(...)` can take a `RegExp`, in which case any path matching the Regular Expression with a fitting method will be used.
 *
 * If multiple mock paths match a path, the latest defined will be used.
 *
 * `clearMocks()` can be used to reset all mock return values set with `.mock()`
 */
export const mockFetcher = {
    path: (path: Path | RegExp) => ({
        method: (method: Method) => ({
            // prettier-ignore
            create: () => async (...args: any[]) => getMockReturn(path as Path, method, args),
            mock: (mockReturn: any) => setMockReturn(path, method, mockReturn),
        }),
    }),
    clearMocks: () => {
        mockValues.length = 0;
    },
};

export const fetcher = mockFetcher;
