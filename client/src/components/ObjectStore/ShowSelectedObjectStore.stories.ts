import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeRegisteredUser } from "@tests/test-data";
import { withCurrentUser } from "@tests/test-data/currentUser";
import { getFakeObjectStoreInstance } from "@tests/test-data/objectStores";

import type { ConcreteObjectStoreModel } from "@/api";
import { http } from "@/api/client/__mocks__/http";

import ShowSelectedObjectStore from "./ShowSelectedObjectStore.vue";

const GALAXY_STORAGE: ConcreteObjectStoreModel = {
    object_store_id: "shared_scratch",
    name: "Shared scratch",
    description: "Shared **scratch storage** on this Galaxy. Move completed analyses to your archive.",
    private: false,
    quota: { enabled: false, source: null },
    badges: [{ type: "no_quota", message: null, source: "galaxy" }],
};
const USER_STORAGE_UUID = "f2db41e1-fa33-4b3e-8a27-134d945ac093";
const USER_STORAGE = getFakeObjectStoreInstance({
    uuid: USER_STORAGE_UUID,
    object_store_id: `user_objects://${USER_STORAGE_UUID}`,
    type: "disk",
    name: "RNA-seq project scratch",
    description: "Scratch storage for **my RNA-seq project**. This location is private.",
    template_id: "project_scratch",
    template_version: 0,
    variables: { project_name: "rna_seq" },
    private: true,
    quota: { enabled: false, source: null },
    badges: [
        { type: "faster", message: null, source: "admin" },
        { type: "less_secure", message: null, source: "admin" },
        { type: "not_backed_up", message: null, source: "admin" },
        { type: "no_quota", message: null, source: "galaxy" },
        { type: "restricted", message: null, source: "galaxy" },
        { type: "user_defined", message: null, source: "galaxy" },
    ],
});

const meta = {
    title: "ObjectStore/ShowSelectedObjectStore",
    component: ShowSelectedObjectStore,
    decorators: [
        withCurrentUser(() =>
            getFakeRegisteredUser({ id: "f2db41e1fa331b3e", email: "alice@example.org", username: "alice" }),
        ),
    ],
    args: { forWhat: "New datasets will be stored in", preferredObjectStoreId: GALAXY_STORAGE.object_store_id! },
    parameters: {
        msw: {
            handlers: {
                galaxyStorage: http.get("/api/object_stores/{object_store_id}", ({ response }) =>
                    response(200).json(GALAXY_STORAGE),
                ),
                userStorage: http.get("/api/object_store_instances/{uuid}", ({ response }) =>
                    response(200).json(USER_STORAGE),
                ),
            },
        },
    },
} satisfies Meta<typeof ShowSelectedObjectStore>;

export default meta;
type Story = StoryObj<typeof meta>;

/** The history's selected Galaxy-managed storage, shared rather than private. */
export const GalaxyStorage: Story = {};

/** The user's own project-scratch instance, loaded through its user_objects URI. */
export const UserStorage: Story = {
    args: { preferredObjectStoreId: USER_STORAGE.object_store_id! },
};
