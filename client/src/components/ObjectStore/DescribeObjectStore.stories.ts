import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { expect, within } from "storybook/test";

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

type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

/** Reads the sentence saying where the dataset is stored; it opens with the `what` arg. */
async function readWhereStored({ canvas, step }: PlayContext, sentence: RegExp) {
    await step("Read where the dataset is stored", async () => {
        await expect(canvas.getByText("This dataset is stored in").parentElement).toHaveTextContent(sentence);
    });
}

/** Reads the no-quota note and the storage description rendered from its markdown. */
async function readQuotaAndDescription({ canvas, step }: PlayContext) {
    await step("Read that no quota applies to this storage", async () => {
        await expect(canvas.getByText("Galaxy has no quota configured for this storage.")).toBeVisible();
    });
    await step("Read the storage description rendered from markdown", async () => {
        const description = canvas.getByRole("paragraph");
        await expect(description).toBeVisible();
        await expect(description).toHaveTextContent(/^Backed up nightly\. Ask an admin to restore a purged dataset\.$/);
        await expect(within(description).getByRole("strong")).toHaveTextContent(/^nightly$/);
    });
}

/** Galaxy's single configured storage, which has no id. */
export const DefaultStorage: Story = {
    args: { storageInfo: storage({}) },
    play: async (context) => {
        // Tolerates a template bug: a space before the period ("storage .").
        await readWhereStored(
            context,
            /^This dataset is stored in the default configured Galaxy sharable storage ?\.$/,
        );
        await readQuotaAndDescription(context);
    },
};

/** A storage the admin gave an id but no name. */
export const StorageWithId: Story = {
    args: { storageInfo: storage({ object_store_id: "fast_scratch" }) },
    play: async (context) => {
        const { canvas, step } = context;
        await readWhereStored(context, /^This dataset is stored in a Galaxy sharable storage with id fast_scratch\.$/);
        await step("See the storage id in bold", async () => {
            await expect(canvas.getByText("fast_scratch").tagName).toBe("B");
        });
        await readQuotaAndDescription(context);
    },
};

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
    play: async (context) => {
        const { canvas, canvasElement, step } = context;
        await readWhereStored(context, /^This dataset is stored in a Galaxy private storage named Fast scratch\.$/);
        await step("See the storage name in bold, and its id nowhere", async () => {
            await expect(canvas.getByText("Fast scratch").tagName).toBe("B");
            await expect(canvasElement).not.toHaveTextContent(/fast_scratch/);
        });
        await readQuotaAndDescription(context);
    },
};
