import { type ObjectStoreTemplateType } from "@/api/objectStores";
import { type ObjectStoreTemplateSummaries } from "@/api/objectStores.templates";
import { useObjectStoreTemplatesStore } from "@/stores/objectStoreTemplatesStore";

import { setupTestPinia } from "./testUtils";

const s3 = "aws_s3" as ObjectStoreTemplateType;
const TEMPLATES_BASIC: ObjectStoreTemplateSummaries = [
    {
        type: s3,
        name: "moo",
        description: null,
        variables: [],
        secrets: [],
        id: "moo",
        version: 0,
        badges: [],
        hidden: false,
    },
];

const TEMPLATES_EXPANDED: ObjectStoreTemplateSummaries = [
    {
        type: s3,
        name: "Testing S3",
        description: null,
        variables: [],
        secrets: [],
        id: "bucket_s3",
        version: 0,
        badges: [],
        hidden: false,
    },
    {
        type: s3,
        name: "Testing S3 (some more)",
        description: null,
        variables: [],
        secrets: [],
        id: "bucket_s3",
        version: 1,
        badges: [],
        hidden: false,
    },
    {
        type: s3,
        name: "Amazon S3 (working!)",
        description: null,
        variables: [],
        secrets: [],
        id: "bucket_s3",
        version: 2,
        badges: [],
        hidden: false,
    },
];

describe("Object Store Templates Store", () => {
    beforeEach(setupTestPinia);

    it("should not be fetched initially", () => {
        const objectStoreTemplateStore = useObjectStoreTemplatesStore();
        expect(objectStoreTemplateStore.fetched).toBeFalsy();
    });

    it("should not be in error initially", () => {
        const objectStoreTemplateStore = useObjectStoreTemplatesStore();
        expect(objectStoreTemplateStore.error).toBeFalsy();
    });

    it("should populate store with handleInit", () => {
        const objectStoreTemplateStore = useObjectStoreTemplatesStore();
        objectStoreTemplateStore.handleInit(TEMPLATES_BASIC);
        expect(objectStoreTemplateStore.templates).toHaveLength(1);
        expect(objectStoreTemplateStore.fetched).toBeTruthy();
    });

    it("should find specific templates when multiple versions are available", () => {
        const objectStoreTemplateStore = useObjectStoreTemplatesStore();
        objectStoreTemplateStore.handleInit(TEMPLATES_EXPANDED);
        expect(objectStoreTemplateStore.templates).toHaveLength(3);
        expect(objectStoreTemplateStore.fetched).toBeTruthy();
        const t1 = objectStoreTemplateStore.getTemplate("bucket_s3", 1);
        expect(t1?.name).toBe("Testing S3 (some more)");
        const t2 = objectStoreTemplateStore.getTemplate("bucket_s3", 2);
        expect(t2?.name).toBe("Amazon S3 (working!)");
    });

    it("should define latest version getter that is collapsed", () => {
        const objectStoreTemplateStore = useObjectStoreTemplatesStore();
        objectStoreTemplateStore.handleInit(TEMPLATES_EXPANDED);
        expect(objectStoreTemplateStore.latestTemplates).toHaveLength(1);
        const latestVersion = objectStoreTemplateStore.latestTemplates[0];
        expect(latestVersion?.name).toBe("Amazon S3 (working!)");
    });

    it("should track what versions allow upgrade", () => {
        const objectStoreTemplateStore = useObjectStoreTemplatesStore();
        objectStoreTemplateStore.handleInit(TEMPLATES_EXPANDED);
        expect(objectStoreTemplateStore.canUpgrade("bucket_s3", 0)).toBeTruthy();
        expect(objectStoreTemplateStore.canUpgrade("bucket_s3", 1)).toBeTruthy();
        expect(objectStoreTemplateStore.canUpgrade("bucket_s3", 2)).toBeFalsy();
    });

    it("should populate an error with handleError", () => {
        const objectStoreTemplateStore = useObjectStoreTemplatesStore();
        objectStoreTemplateStore.handleError(Error("an error"));
        expect(objectStoreTemplateStore.error).toBe("an error");
    });
});
