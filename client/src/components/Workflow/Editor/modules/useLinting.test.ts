import { createTestingPinia } from "@pinia/testing";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { type Ref, ref } from "vue";

import type { Creator } from "@/api/workflows";
import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
import type { Steps } from "@/stores/workflowStepStore";

import lintStepsData from "../test-data/lint_steps.json";
import { useLintData } from "./useLinting";

const steps: Steps = lintStepsData as unknown as Steps;

describe("useLintData", () => {
    let stepsRef: Ref<Steps>;

    beforeEach(() => {
        const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
        setActivePinia(pinia);
        stepsRef = ref(steps);
    });

    describe("priority issue counting", () => {
        it("counts priority issues correctly with all metadata provided", () => {
            const lintData = useLintData(
                ref("test-workflow"),
                stepsRef,
                ref(testDatatypesMapper),
                ref("workflow annotation"),
                ref("workflow readme"),
                ref("MIT"),
                ref([
                    {
                        class: "Person",
                        name: "Test Creator",
                    },
                ]),
            );

            // Priority issues that exist in our test setup:
            // - untypedParameters: exists=true (has steps), resolved=false (has untyped param)
            // - disconnectedInputs: exists=true (has steps), resolved=false (has disconnected input)
            // - noOutputs: exists=true (no active outputs in fresh store), resolved=false
            expect(lintData.totalPriorityIssues.value).toBe(3);
            expect(lintData.resolvedPriorityIssues.value).toBe(0);
        });

        it("counts priority issues correctly with no metadata provided", () => {
            const lintData = useLintData(
                ref("test-workflow"),
                stepsRef,
                ref(testDatatypesMapper),
                ref(null),
                ref(null),
                ref(null),
                ref(null),
            );

            // Priority issues remain the same regardless of metadata
            expect(lintData.totalPriorityIssues.value).toBe(3);
            expect(lintData.resolvedPriorityIssues.value).toBe(0);
        });

        it("correctly handles empty steps scenario", () => {
            const emptyStepsRef = ref({});
            const lintData = useLintData(
                ref("test-workflow"),
                emptyStepsRef,
                ref(testDatatypesMapper),
                ref("workflow annotation"),
                ref("workflow readme"),
                ref("MIT"),
                ref([
                    {
                        class: "Person",
                        name: "Test Creator",
                    },
                ]),
            );

            // With no steps:
            // - untypedParameters: exists=false (no steps)
            // - disconnectedInputs: exists=false (no steps)
            // - missingMetadata: exists=false (no input steps)
            // - duplicateLabels: exists=false (no outputs)
            // - unlabeledOutputs: exists=false (no outputs)
            // - noOutputs: exists=true (no outputs), resolved=false
            expect(lintData.totalPriorityIssues.value).toBe(1); // Only noOutputs
            expect(lintData.resolvedPriorityIssues.value).toBe(0); // noOutputs is never resolved
        });

        it("correctly identifies untyped parameters", () => {
            const lintData = useLintData(
                ref("test-workflow"),
                stepsRef,
                ref(testDatatypesMapper),
                ref("workflow annotation"),
                ref("workflow readme"),
                ref("MIT"),
                ref([
                    {
                        class: "Person",
                        name: "Test Creator",
                    },
                ]),
            );

            expect(lintData.untypedParameterWarnings.value).toHaveLength(1);
            expect(lintData.untypedParameterWarnings.value[0]!.name).toBe("untyped_parameter");
        });

        it("correctly identifies disconnected inputs", () => {
            const lintData = useLintData(
                ref("test-workflow"),
                stepsRef,
                ref(testDatatypesMapper),
                ref("workflow annotation"),
                ref("workflow readme"),
                ref("MIT"),
                ref([
                    {
                        class: "Person",
                        name: "Test Creator",
                    },
                ]),
            );

            expect(lintData.disconnectedInputs.value).toHaveLength(1);
        });

        it("correctly identifies unlabeled outputs", () => {
            const lintData = useLintData(
                ref("test-workflow"),
                stepsRef,
                ref(testDatatypesMapper),
                ref("workflow annotation"),
                ref("workflow readme"),
                ref("MIT"),
                ref([
                    {
                        class: "Person",
                        name: "Test Creator",
                    },
                ]),
            );

            // Step 1 has workflow_outputs with no label
            expect(lintData.unlabeledOutputs.value).toHaveLength(1);
        });
    });

    describe("attribute issue counting", () => {
        it("counts all attribute issues as resolved when all metadata is provided", () => {
            const lintData = useLintData(
                ref("test-workflow"),
                stepsRef,
                ref(testDatatypesMapper),
                ref("workflow annotation"),
                ref("workflow readme"),
                ref("MIT"),
                ref([
                    {
                        class: "Person",
                        name: "Test Creator",
                    },
                ]),
            );

            // Attribute issues always exist: annotation, readme, creator, license
            expect(lintData.totalAttributeIssues.value).toBe(4);
            // All are resolved since we provided all metadata
            expect(lintData.resolvedAttributeIssues.value).toBe(4);
        });

        it("counts unresolved attribute issues when no metadata is provided", () => {
            const lintData = useLintData(
                ref("test-workflow"),
                stepsRef,
                ref(testDatatypesMapper),
                ref(null),
                ref(null),
                ref(null),
                ref(null),
            );

            // Attribute issues: annotation, readme, creator, license all exist but none resolved
            expect(lintData.totalAttributeIssues.value).toBe(4);
            expect(lintData.resolvedAttributeIssues.value).toBe(0);
        });

        it("counts annotationLength issue when annotation is too long", () => {
            const longAnnotation = "a".repeat(300); // More than 250 characters
            const lintData = useLintData(
                ref("test-workflow"),
                stepsRef,
                ref(testDatatypesMapper),
                ref(longAnnotation),
                ref("workflow readme"),
                ref("MIT"),
                ref([
                    {
                        class: "Person",
                        name: "Test Creator",
                    },
                ]),
            );

            // Now we should have 5 attribute issues: annotation, annotationLength, readme, creator, license
            expect(lintData.totalAttributeIssues.value).toBe(5);
            // annotation is resolved (exists), annotationLength is NOT resolved (too long),
            // plus readme, creator, license are resolved = 4 resolved
            expect(lintData.resolvedAttributeIssues.value).toBe(4);
        });

        it("does not count annotationLength issue when annotation is within limit", () => {
            const shortAnnotation = "a".repeat(100); // Less than 250 characters
            const lintData = useLintData(
                ref("test-workflow"),
                stepsRef,
                ref(testDatatypesMapper),
                ref(shortAnnotation),
                ref("workflow readme"),
                ref("MIT"),
                ref([
                    {
                        class: "Person",
                        name: "Test Creator",
                    },
                ]),
            );

            // Should have 4 attribute issues: annotation, readme, creator, license
            // annotationLength doesn't exist when annotation is within limit
            expect(lintData.totalAttributeIssues.value).toBe(4);
            expect(lintData.resolvedAttributeIssues.value).toBe(4);
        });

        it("verifies individual check flags", () => {
            const lintData = useLintData(
                ref("test-workflow"),
                stepsRef,
                ref(testDatatypesMapper),
                ref("workflow annotation"),
                ref("workflow readme"),
                ref("MIT"),
                ref([
                    {
                        class: "Person",
                        name: "Test Creator",
                    },
                ]),
            );

            expect(lintData.checkAnnotation.value).toBe(true);
            expect(lintData.checkAnnotationLength.value).toBe(true);
            expect(lintData.checkReadme.value).toBe(true);
            expect(lintData.checkLicense.value).toBe(true);
            expect(lintData.checkCreator.value).toBe(true);
        });

        it("verifies individual check flags when metadata is missing", () => {
            const lintData = useLintData(
                ref("test-workflow"),
                stepsRef,
                ref(testDatatypesMapper),
                ref(null),
                ref(null),
                ref(null),
                ref(null),
            );

            expect(lintData.checkAnnotation.value).toBe(false);
            expect(lintData.checkAnnotationLength.value).toBe(false);
            expect(lintData.checkReadme.value).toBe(false);
            expect(lintData.checkLicense.value).toBe(false);
            expect(lintData.checkCreator.value).toBe(false);
        });
    });

    describe("reactive updates", () => {
        it("reactively updates counts when annotation changes", async () => {
            const annotation = ref<string | null>(null);

            const lintData = useLintData(
                ref("test-workflow"),
                stepsRef,
                ref(testDatatypesMapper),
                annotation,
                ref("workflow readme"),
                ref("MIT"),
                ref([
                    {
                        class: "Person",
                        name: "Test Creator",
                    },
                ]),
            );

            // Initially no annotation
            expect(lintData.resolvedAttributeIssues.value).toBe(3); // readme, license, creator

            // Add annotation
            annotation.value = "My workflow";
            expect(lintData.resolvedAttributeIssues.value).toBe(4); // All resolved
        });

        it("reactively updates counts when readme changes", async () => {
            const readme = ref<string | null>(null);

            const lintData = useLintData(
                ref("test-workflow"),
                stepsRef,
                ref(testDatatypesMapper),
                ref("workflow annotation"),
                readme,
                ref("MIT"),
                ref([
                    {
                        class: "Person",
                        name: "Test Creator",
                    },
                ]),
            );

            // Initially no readme
            expect(lintData.resolvedAttributeIssues.value).toBe(3); // annotation, license, creator

            // Add readme
            readme.value = "My readme";
            expect(lintData.resolvedAttributeIssues.value).toBe(4); // All resolved
        });

        it("reactively adds annotationLength issue when annotation becomes too long", async () => {
            const annotation = ref<string | null>("Short annotation");

            const lintData = useLintData(
                ref("test-workflow"),
                stepsRef,
                ref(testDatatypesMapper),
                annotation,
                ref("workflow readme"),
                ref("MIT"),
                ref([
                    {
                        class: "Person",
                        name: "Test Creator",
                    },
                ]),
            );

            // Initially annotation is short
            expect(lintData.totalAttributeIssues.value).toBe(4);
            expect(lintData.resolvedAttributeIssues.value).toBe(4);

            // Make annotation too long
            annotation.value = "a".repeat(300);
            expect(lintData.totalAttributeIssues.value).toBe(5); // annotationLength now exists
            expect(lintData.resolvedAttributeIssues.value).toBe(4); // annotation still resolved, but not annotationLength
        });

        it("reactively updates when license changes", async () => {
            const license = ref<string | null>(null);

            const lintData = useLintData(
                ref("test-workflow"),
                stepsRef,
                ref(testDatatypesMapper),
                ref("workflow annotation"),
                ref("workflow readme"),
                license,
                ref([
                    {
                        class: "Person",
                        name: "Test Creator",
                    },
                ]),
            );

            // Initially no license
            expect(lintData.resolvedAttributeIssues.value).toBe(3); // annotation, readme, creator

            // Add license
            license.value = "MIT";
            expect(lintData.resolvedAttributeIssues.value).toBe(4); // All resolved
        });

        it("reactively updates when creator changes", async () => {
            const creator = ref<Creator[] | null>(null);

            const lintData = useLintData(
                ref("test-workflow"),
                stepsRef,
                ref(testDatatypesMapper),
                ref("workflow annotation"),
                ref("workflow readme"),
                ref("MIT"),
                creator,
            );

            // Initially no creator
            expect(lintData.resolvedAttributeIssues.value).toBe(3); // annotation, readme, license

            // Add creator
            creator.value = [{ class: "Person", name: "Test Creator" }];
            expect(lintData.resolvedAttributeIssues.value).toBe(4); // All resolved
        });
    });

    describe("warning detection", () => {
        it("returns refs for all warning types", () => {
            const lintData = useLintData(
                ref("test-workflow"),
                stepsRef,
                ref(testDatatypesMapper),
                ref("workflow annotation"),
                ref("workflow readme"),
                ref("MIT"),
                ref([
                    {
                        class: "Person",
                        name: "Test Creator",
                    },
                ]),
            );

            // All warning arrays should be refs (even if empty)
            expect(lintData.untypedParameterWarnings.value).toBeDefined();
            expect(lintData.disconnectedInputs.value).toBeDefined();
            expect(lintData.duplicateLabels.value).toBeDefined();
            expect(lintData.unlabeledOutputs.value).toBeDefined();
            expect(lintData.missingMetadata.value).toBeDefined();
            expect(Array.isArray(lintData.untypedParameterWarnings.value)).toBe(true);
            expect(Array.isArray(lintData.disconnectedInputs.value)).toBe(true);
            expect(Array.isArray(lintData.duplicateLabels.value)).toBe(true);
            expect(Array.isArray(lintData.unlabeledOutputs.value)).toBe(true);
            expect(Array.isArray(lintData.missingMetadata.value)).toBe(true);
        });
    });
});
