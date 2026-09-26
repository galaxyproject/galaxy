import { beforeEach, describe, expect, it, vi } from "vitest";
import { reactive, ref } from "vue";

import {
    getUploadMethod,
    uploadMethodRegistry,
    useAllUploadMethods,
    useFilteredUploadMethods,
} from "./uploadMethodRegistry";

// The advancedMode ref is declared before the vi.mock call so both the mock factory
// and the test bodies share the same reactive reference.
const advancedMode = ref(false);

vi.mock("@/composables/upload/uploadAdvancedMode", () => ({
    useUploadAdvancedMode: () => ({ advancedMode }),
}));

// Reactive state object for useUserStore mock — storeToRefs expects a reactive object.
const userStoreState = reactive({ isAnonymous: true });

vi.mock("@/stores/userStore", () => ({
    useUserStore: () => userStoreState,
}));

// Reactive refs for useConfig mock.
const galaxyConfig = ref({});
const isConfigLoaded = ref(true);

vi.mock("@/composables/config", () => ({
    useConfig: () => ({ config: galaxyConfig, isConfigLoaded }),
}));

// Derive method ID lists from the registry so they stay in sync automatically
// whenever a method is added, removed, or promoted/demoted to advanced mode.
const ALL_METHOD_IDS = Object.keys(uploadMethodRegistry) as Array<keyof typeof uploadMethodRegistry>;
const ADVANCED_METHOD_IDS = ALL_METHOD_IDS.filter((id) => uploadMethodRegistry[id].requiresAdvancedMode);
const STANDARD_METHOD_IDS = ALL_METHOD_IDS.filter((id) => !uploadMethodRegistry[id].requiresAdvancedMode);
const LOGIN_METHOD_IDS = ALL_METHOD_IDS.filter((id) => uploadMethodRegistry[id].requiresLogin);

describe("uploadMethodRegistry", () => {
    describe("getUploadMethod", () => {
        it("returns the matching config for a known ID", () => {
            const config = getUploadMethod("local-file");
            expect(config?.id).toBe("local-file");
            expect(config?.name).toBe("Upload from Computer");
        });

        it("returns undefined for an unknown ID", () => {
            expect(getUploadMethod("nonexistent" as never)).toBeUndefined();
        });
    });

    describe("useAllUploadMethods", () => {
        beforeEach(() => {
            advancedMode.value = false;
        });

        it("excludes all advanced-mode methods when advancedMode is false", () => {
            const methods = useAllUploadMethods();
            const ids = methods.value.map((m) => m.id);

            for (const advancedId of ADVANCED_METHOD_IDS) {
                expect(ids).not.toContain(advancedId);
            }
            expect(ids).toHaveLength(STANDARD_METHOD_IDS.length);
        });

        it("reacts to advancedMode changes without creating a new composable instance", () => {
            const methods = useAllUploadMethods();

            expect(methods.value).toHaveLength(STANDARD_METHOD_IDS.length);

            advancedMode.value = true;
            expect(methods.value).toHaveLength(ALL_METHOD_IDS.length);

            advancedMode.value = false;
            expect(methods.value).toHaveLength(STANDARD_METHOD_IDS.length);
        });
    });

    describe("useFilteredUploadMethods", () => {
        beforeEach(() => {
            advancedMode.value = false;
            userStoreState.isAnonymous = true;
            isConfigLoaded.value = true;
        });

        it("disables login-required methods when user is anonymous", () => {
            const methods = useFilteredUploadMethods();

            for (const loginId of LOGIN_METHOD_IDS) {
                const method = methods.value.find((m) => m.id === loginId);
                expect(method).toBeDefined();
                expect(method?.disabled).toBe(true);
                expect(method?.disabledTitle).toBeDefined();
            }
        });

        it("includes login-required methods without disabled when user is logged in", () => {
            userStoreState.isAnonymous = false;
            const methods = useFilteredUploadMethods();

            for (const loginId of LOGIN_METHOD_IDS) {
                const method = methods.value.find((m) => m.id === loginId);
                expect(method).toBeDefined();
                expect(method?.disabled).toBeFalsy();
                expect(method?.disabledTitle).toBeUndefined();
            }
        });

        it("filters by allowedMethods when provided", () => {
            const allowedMethods = ref(["local-file", "paste-content"] as ["local-file", "paste-content"]);
            const methods = useFilteredUploadMethods(allowedMethods);
            const ids = methods.value.map((m) => m.id);

            expect(ids).toContain("local-file");
            expect(ids).toContain("paste-content");
            expect(ids).not.toContain("paste-links");
        });
    });
});
