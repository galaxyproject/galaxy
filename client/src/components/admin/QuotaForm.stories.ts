import type { Meta, StoryObj } from "@storybook/vue3-vite";

import type { components } from "@/api";
import { configurationHandler, http } from "@/api/client/__mocks__/http";

import { ADMIN_GROUPS, ADMIN_USER, adminGroups, adminUserSearch } from "./test_fixtures";

import QuotaForm from "./QuotaForm.vue";

type QuotaDetails = components["schemas"]["QuotaDetails"];

const MEMBER_GROUP = ADMIN_GROUPS[0]!;

/** A 1.2 GB quota assigned to one user and one group. */
const QUOTA: QuotaDetails = {
    id: "7c3e9a1f5b2d8e40",
    model_class: "Quota",
    name: "Workshop participants",
    description: "Extra space for the RNA-seq workshop",
    bytes: 1234567890,
    operation: "=",
    display_amount: "1.2 GB",
    default: [],
    users: [
        {
            model_class: "UserQuotaAssociation",
            user: {
                ...ADMIN_USER,
                active: true,
                deleted: false,
                last_password_change: null,
                model_class: "User",
            },
        },
    ],
    groups: [
        {
            model_class: "GroupQuotaAssociation",
            group: { id: MEMBER_GROUP.id, name: MEMBER_GROUP.name, model_class: "Group" },
        },
    ],
};

/** Answers the form's request for the quota being edited. */
function quotaDetails(details: QuotaDetails) {
    return http.get("/api/quotas/{id}", ({ response }) => response(200).json(details));
}

const meta = {
    title: "admin/QuotaForm",
    component: QuotaForm,
    parameters: {
        msw: {
            handlers: {
                groups: adminGroups(),
                userSearch: adminUserSearch(),
                quota: quotaDetails(QUOTA),
                createQuota: http.post("/api/quotas", async ({ request, response }) => {
                    const { name, quota_source_label, in_users, in_groups } = await request.json();
                    return response(200).json({
                        id: "2a9f4e7c1b6d3e85",
                        model_class: "Quota",
                        name,
                        url: "/api/quotas/2a9f4e7c1b6d3e85",
                        message: `Quota '${name}' has been created with ${in_users?.length ?? 0} associated users and ${in_groups?.length ?? 0} associated groups.`,
                        quota_source_label,
                    });
                }),
                updateQuota: http.put("/api/quotas/{id}", ({ response }) =>
                    response(200).json(
                        `Quota '${QUOTA.name}' has been updated with 1 associated users and 1 associated groups.`,
                    ),
                ),
            },
        },
    },
} satisfies Meta<typeof QuotaForm>;

export default meta;
type Story = StoryObj<typeof meta>;

/** An empty form for a new quota on a Galaxy with unlabeled storage. Name, description and amount are required. */
export const NewQuota: Story = {};

/** A Galaxy whose object stores carry quota labels asks which storage the new quota applies to. */
export const NewQuotaForLabeledStorage: Story = {
    parameters: {
        msw: { handlers: { configuration: configurationHandler({ quota_source_labels: ["scratch"] }) } },
    },
};

/** An existing quota with its user and group selected. */
export const ExistingQuota: Story = {
    args: { quotaId: QUOTA.id },
};

/** The default quota for registered users: it can't have users or groups, so those pickers are hidden. */
export const ExistingDefaultQuota: Story = {
    args: { ...ExistingQuota.args },
    parameters: {
        msw: {
            handlers: {
                quota: quotaDetails({
                    ...QUOTA,
                    default: [{ model_class: "DefaultQuotaAssociation", type: "registered" }],
                    users: [],
                    groups: [],
                }),
            },
        },
    },
};

/** The quota was deleted in another tab, so the form isn't shown and nothing can be saved. */
export const ExistingQuotaDeleted: Story = {
    args: { ...ExistingQuota.args },
    parameters: {
        msw: {
            handlers: {
                quota: http.get("/api/quotas/{id}", ({ response }) =>
                    response("4XX").json({ err_msg: `Quota "${QUOTA.name}" is deleted`, err_code: 0 }, { status: 400 }),
                ),
            },
        },
    },
};
