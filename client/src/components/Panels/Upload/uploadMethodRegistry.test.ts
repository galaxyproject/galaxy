import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { getUploadMethod, uploadMethodRegistry, useAllUploadMethods } from "./uploadMethodRegistry";

// The advancedMode ref is declared before the vi.mock call so both the mock factory
// and the test bodies share the same reactive reference.
const advancedMode = ref(false);

vi.mock("@/composables/upload/uploadAdvancedMode", () => ({
    useUploadAdvancedMode: () => ({ advancedMode }),
}));

// Derive method ID lists from the registry so they stay in sync automatically
// whenever a method is added, removed, or promoted/demoted to advanced mode.
const ALL_METHOD_IDS = Object.keys(uploadMethodRegistry) as Array<keyof typeof uploadMethodRegistry>;
const ADVANCED_METHOD_IDS = ALL_METHOD_IDS.filter((id) => uploadMethodRegistry[id].requiresAdvancedMode);
const STANDARD_METHOD_IDS = ALL_METHOD_IDS.filter((id) => !uploadMethodRegistry[id].requiresAdvancedMode);

describe("uploadMethodRegistry", () => {
    describe("getUploadMethod", () => {
        it("returns the matching config for a known ID", () => {
            const config = getUploadMethod("local-file");
            expect(config?.id).toBe("local-file");
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
});
