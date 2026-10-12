import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withCurrentUser } from "@tests/test-data/currentUser";
import { withToasts } from "@tests/test-data/toasts";
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
