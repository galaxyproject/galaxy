import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withCurrentUser } from "@tests/test-data/currentUser";
import { seeToasts, withToasts } from "@tests/test-data/toasts";
import { expect } from "storybook/test";
import { h, ref } from "vue";

import { http } from "@/api/client/__mocks__/http";

import { PERSONAL_DISK_STORE, withObjectStoreTemplates } from "./test_fixtures";

import InstanceDropdown from "./InstanceDropdown.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";

const meta = {
    title: "ObjectStore/Instances/InstanceDropdown",
    component: InstanceDropdown,
    args: { objectStore: PERSONAL_DISK_STORE },
    decorators: [withCurrentUser(), withObjectStoreTemplates(), withToasts],
    // The management page reloads its list after entryRemoved and filters out hidden instances.
    render: (args) => ({
        setup() {
            const removed = ref(false);
            return () =>
                removed.value
                    ? h(GAlert, { variant: "info" }, () => "No Galaxy storage instances found.")
                    : h(InstanceDropdown, { ...args, onEntryRemoved: () => (removed.value = true) });
        },
    }),
    parameters: {
        msw: {
            handlers: {
                update: http.put("/api/object_store_instances/{uuid}", async ({ request, response }) => {
                    const payload = await request.json();
                    return response(200).json({
                        ...PERSONAL_DISK_STORE,
                        hidden:
                            "hidden" in payload
                                ? (payload.hidden ?? PERSONAL_DISK_STORE.hidden)
                                : PERSONAL_DISK_STORE.hidden,
                    });
                }),
            },
        },
    },
} satisfies Meta<typeof InstanceDropdown>;
export default meta;
type Story = StoryObj<typeof meta>;
type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

async function openOperations({ canvas, userEvent }: PlayContext) {
    const button = await canvas.findByRole("button", { name: PERSONAL_DISK_STORE.name || "" }, { timeout: 5000 });
    await expect(canvas.queryByRole("button", { name: "Remove instance" })).not.toBeInTheDocument();
    await userEvent.click(button);
    await expect(await canvas.findByRole("button", { name: "Remove instance" })).toBeVisible();
}

/** Removing a private disk instance hides it from the user's storage list. */
export const RemovableStorage: Story = {};

/** The cached row remains visible after another session has already deleted the instance. */
export const StorageNoLongerExists: Story = {
    parameters: {
        msw: {
            handlers: {
                update: http.put("/api/object_store_instances/{uuid}", ({ params, response }) =>
                    response("4XX").json(
                        { err_code: 400008, err_msg: `Failed to fetch object store for id ${params.uuid}` },
                        { status: 400 },
                    ),
                ),
            },
        },
    },
};

/** Remove the instance through its menu and see the management page's empty state. */
export const RemovesStorage: Story = {
    play: async (context) => {
        const { canvas, userEvent, step } = context;
        await step("Open the storage instance's operations", async () => openOperations(context));
        await step("Remove the instance from the storage list", async () => {
            await userEvent.click(canvas.getByRole("button", { name: "Remove instance" }));
            await expect(
                await canvas.findByText("No Galaxy storage instances found.", {}, { timeout: 5000 }),
            ).toBeVisible();
            await seeToasts(canvas, []);
            await expect(
                canvas.queryByRole("button", { name: PERSONAL_DISK_STORE.name || "" }),
            ).not.toBeInTheDocument();
            await expect(canvas.queryByRole("button", { name: "Remove instance" })).not.toBeInTheDocument();
        });
    },
};

/** A stale instance fails to remove: the toast explains Galaxy's error and the list keeps its row. */
export const KeepsStorageAfterRefusal: Story = {
    parameters: StorageNoLongerExists.parameters,
    play: async (context) => {
        const { canvas, userEvent, step } = context;
        await step("Open the storage instance's operations", async () => openOperations(context));
        await step("Read Galaxy's refusal and keep the storage instance", async () => {
            await userEvent.click(canvas.getByRole("button", { name: "Remove instance" }));
            await seeToasts(canvas, [
                ["Failed to remove instance", `Failed to fetch object store for id ${PERSONAL_DISK_STORE.uuid}`],
            ]);
            const button = canvas.getByRole("button", { name: PERSONAL_DISK_STORE.name || "" });
            await expect(button).toBeVisible();
            await expect(
                canvas.queryByText("No Galaxy storage instances found.", { exact: true }),
            ).not.toBeInTheDocument();
            await expect(button).toHaveAttribute("aria-expanded", "false");
            await expect(canvas.queryByRole("button", { name: "Remove instance" })).not.toBeInTheDocument();
        });
    },
};
