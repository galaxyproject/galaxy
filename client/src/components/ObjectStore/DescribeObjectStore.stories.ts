import type { Meta, StoryObj } from "@storybook/vue3-vite";

import type { DatasetStorageDetails } from "@/api";

import DescribeObjectStore from "./DescribeObjectStore.vue";

/** A dataset's storage details as `/api/datasets/{id}/storage` returns them, without quota. */
function storage(details: Partial<DatasetStorageDetails>): DatasetStorageDetails {
    return {
        object_store_id: null,
        name: null,
        description: "Backed up **nightly**. Ask an admin to restore a purged dataset.",
        dataset_state: "ok",
        quota: { enabled: false, source: null },
        relocatable: false,
        shareable: true,
        badges: [],
        hashes: [],
        sources: [],
        percent_used: null,
        private: false,
        ...details,
    };
}

const meta = {
    title: "ObjectStore/DescribeObjectStore",
    component: DescribeObjectStore,
    args: { what: "This dataset is stored in" },
} satisfies Meta<typeof DescribeObjectStore>;

export default meta;
type Story = StoryObj<typeof meta>;

/** Galaxy's single configured storage, which has no id. */
export const DefaultStorage: Story = { args: { storageInfo: storage({}) } };

/** A storage the admin gave an id but no name. */
export const StorageWithId: Story = { args: { storageInfo: storage({ object_store_id: "fast_scratch" }) } };

/** A private storage shown by its name rather than its id. */
export const NamedPrivateStorage: Story = {
    args: {
        storageInfo: storage({
            object_store_id: "fast_scratch",
            name: "Fast scratch",
            private: true,
            shareable: false,
        }),
    },
};
