import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { getUploadMethod, uploadMethodRegistry, useAllUploadMethods } from "./uploadMethodRegistry";

// The advancedMode ref is declared before the vi.mock call so both the mock factory
// and the test bodies share the same reactive reference.
const advancedMode = ref(false);

vi.mock("@/composables/upload/uploadAdvancedMode", () => ({
    useUploadAdvancedMode: () => ({ advancedMode }),
}));

// All registered upload method IDs derived from the registry itself, so this list
// stays in sync automatically whenever a method is added or removed.
const ALL_METHOD_IDS = Object.keys(uploadMethodRegistry) as Array<keyof typeof uploadMethodRegistry>;

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

        it("excludes rule-based-import when advancedMode is false", () => {
            const methods = useAllUploadMethods();
            const ids = methods.value.map((m) => m.id);

            expect(ids).not.toContain("rule-based-import");
        });

        it("includes all 10 methods when advancedMode is true", () => {
            advancedMode.value = true;
            const methods = useAllUploadMethods();
            const ids = methods.value.map((m) => m.id);

            expect(ids).toContain("rule-based-import");
        });

        it("reacts to advancedMode changes without creating a new composable instance", () => {
            const methods = useAllUploadMethods();

            expect(methods.value).toHaveLength(9);

            advancedMode.value = true;
            expect(methods.value).toHaveLength(10);

            advancedMode.value = false;
            expect(methods.value).toHaveLength(9);
        });
    });
});
