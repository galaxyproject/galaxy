import type { Decorator } from "@storybook/vue3-vite";
import { getFakeObjectStoreInstance } from "@tests/test-data/objectStores";
import { h } from "vue";

import type { ObjectStoreTemplateSummaries, ObjectStoreTemplateSummary } from "@/api/objectStores.templates";
import { useObjectStoreTemplatesStore } from "@/stores/objectStoreTemplatesStore";

/** The variable-backed disk template from the object-store manager's backend tests. */
export const PERSONAL_DISK_TEMPLATE: ObjectStoreTemplateSummary = {
    id: "simple_variable",
    name: "Simple Variable",
    description: "This is a simple description",
    version: 0,
    type: "disk",
    variables: [{ name: "var1", type: "path_component", help: "This is some simple help." }],
    secrets: [],
    badges: [],
    hidden: false,
};

/** A user's disk instance, including the private-instance fields and Galaxy's automatic badges. */
export const PERSONAL_DISK_STORE = getFakeObjectStoreInstance({
    uuid: "112f889f-72d7-4619-a8e8-510a8c685aa7",
    name: "Workflow results",
    description: "Personal storage for workflow results",
    template_id: PERSONAL_DISK_TEMPLATE.id,
    template_version: PERSONAL_DISK_TEMPLATE.version,
    type: "disk",
    variables: { var1: "workflow-results" },
    object_store_id: "user_objects://112f889f-72d7-4619-a8e8-510a8c685aa7",
    private: true,
    quota: { source: null, enabled: false },
    badges: [
        { type: "no_quota", source: "galaxy", message: null },
        { type: "restricted", source: "galaxy", message: null },
        { type: "user_defined", source: "galaxy", message: null },
    ],
});

/** Seed the story's fresh Pinia with the catalog its instance-management page already loaded. */
export function withObjectStoreTemplates(
    templates: ObjectStoreTemplateSummaries = [PERSONAL_DISK_TEMPLATE],
): Decorator {
    return (story) => ({
        setup() {
            useObjectStoreTemplatesStore().handleInit(templates);
            return () => h(story());
        },
    });
}
