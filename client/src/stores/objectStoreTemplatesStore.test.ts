import { beforeEach, describe, expect, it } from "vitest";

import type { ObjectStoreTemplateSummary } from "@/api/objectStores.templates";
import { useObjectStoreTemplatesStore } from "@/stores/objectStoreTemplatesStore";

import { setupTestPinia } from "./testUtils";

function template(overrides: Partial<ObjectStoreTemplateSummary> = {}): ObjectStoreTemplateSummary {
    return {
        type: "aws_s3",
        name: "moo",
        description: null,
        variables: [],
        secrets: [],
        id: "moo",
        version: 0,
        badges: [],
        hidden: false,
        ...overrides,
    };
}

function versionedTemplates() {
    return [
        template({ id: "bucket_s3", version: 0, name: "Testing S3" }),
        template({ id: "bucket_s3", version: 1, name: "Testing S3 (some more)" }),
        template({ id: "bucket_s3", version: 2, name: "Amazon S3 (working!)" }),
    ];
}

describe("Object Store Templates Store", () => {
    let store: ReturnType<typeof useObjectStoreTemplatesStore>;

    beforeEach(() => {
        setupTestPinia();
        store = useObjectStoreTemplatesStore();
    });

    it("starts without fetched templates", () => {
        expect(store.fetched).toBe(false);
    });

    it("starts without an error", () => {
        expect(store.error).toBeNull();
    });

    it("marks initialized templates as fetched", async () => {
        const templates = [template()];

        await store.handleInit(templates);

        expect(store.templates).toEqual(templates);
        expect(store.templates).toHaveLength(1);
        expect(store.fetched).toBe(true);
    });

    it.each([
        { version: 1, expectedName: "Testing S3 (some more)" },
        { version: 2, expectedName: "Amazon S3 (working!)" },
    ])("finds version $version when several versions are available", async ({ version, expectedName }) => {
        await store.handleInit(versionedTemplates());

        expect(store.templates).toHaveLength(3);
        expect(store.fetched).toBe(true);
        expect(store.getTemplate("bucket_s3", version)?.name).toBe(expectedName);
    });

    it("collapses template versions to the latest one", async () => {
        await store.handleInit(versionedTemplates());

        expect(store.latestTemplates).toHaveLength(1);
        expect(store.latestTemplates[0]?.name).toBe("Amazon S3 (working!)");
    });

    it.each([
        { version: 0, expectedUpgrade: true },
        { version: 1, expectedUpgrade: true },
        { version: 2, expectedUpgrade: false },
    ])("reports upgrade eligibility for version $version", async ({ version, expectedUpgrade }) => {
        await store.handleInit(versionedTemplates());

        expect(store.canUpgrade("bucket_s3", version)).toBe(expectedUpgrade);
    });

    it("records the error message when initialization fails", async () => {
        await store.handleError(Error("an error"));

        expect(store.error).toBe("an error");
    });
});
