import type { UserConcreteObjectStore } from "@/api/objectStores";

export function getFakeObjectStoreInstance(overrides: Partial<UserConcreteObjectStore> = {}): UserConcreteObjectStore {
    return {
        type: "aws_s3",
        name: "Test Object Store",
        description: undefined,
        template_id: "an_s3_template",
        template_version: 0,
        badges: [],
        variables: {},
        secrets: [],
        quota: { enabled: false },
        private: false,
        uuid: "object-store-id",
        active: true,
        hidden: false,
        purged: false,
        ...overrides,
    };
}
