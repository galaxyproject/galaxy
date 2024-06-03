import { type ObjectStoreTemplateType } from "@/api/objectStores";
import { useObjectStoreInstancesStore } from "@/stores/objectStoreInstancesStore";

import { setupTestPinia } from "./testUtils";

const type = "aws_s3" as ObjectStoreTemplateType;
const UUID = "112f889f-72d7-4619-a8e8-510a8c685aa7";
const TEST_INSTANCE = {
    type: type,
    name: "moo",
    description: undefined,
    template_id: "an_s3_template",
    template_version: 0,
    badges: [],
    variables: {},
    secrets: [],
    quota: { enabled: false },
    private: false,
    uuid: UUID,
    active: true,
    hidden: false,
    purged: false,
};

describe("Object Store Instances Store", () => {
    beforeEach(setupTestPinia);

    it("should not be fetched initially", () => {
        const objectStoreInstancesStore = useObjectStoreInstancesStore();
        expect(objectStoreInstancesStore.fetched).toBeFalsy();
    });

    it("should not be in error initially", () => {
        const objectStoreInstancesStore = useObjectStoreInstancesStore();
        expect(objectStoreInstancesStore.error).toBeFalsy();
    });

    it("should populate store with handleInit", () => {
        const objectStoreInstancesStore = useObjectStoreInstancesStore();
        objectStoreInstancesStore.handleInit([TEST_INSTANCE]);
        expect(objectStoreInstancesStore.instances).toHaveLength(1);
        expect(objectStoreInstancesStore.fetched).toBeTruthy();
    });

    it("should allow finding an instance by instance id", () => {
        const objectStoreInstancesStore = useObjectStoreInstancesStore();
        objectStoreInstancesStore.handleInit([TEST_INSTANCE]);
        expect(objectStoreInstancesStore.getInstance(UUID)?.name).toBe("moo");
    });

    it("should populate an error with handleError", () => {
        const objectStoreInstancesStore = useObjectStoreInstancesStore();
        objectStoreInstancesStore.handleError(Error("an error"));
        expect(objectStoreInstancesStore.error).toBe("an error");
    });
});
