import type { Decorator, Meta, StoryObj } from "@storybook/vue3-vite";
import { expect, within } from "storybook/test";
import { h } from "vue";

import type { components } from "@/api";
import { configurationHandler, http } from "@/api/client/__mocks__/http";
import { useConfigStore } from "@/stores/configurationStore";
import { escapeRegExp } from "@/utils/regExp";

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

/** The admin page loads the configuration first; the storage choice depends on it. */
const withLoadedConfig: Decorator = (story) => ({
    setup() {
        const configStore = useConfigStore();
        return () => (configStore.isLoaded ? h(story()) : null);
    },
});

const meta = {
    title: "admin/QuotaForm",
    component: QuotaForm,
    decorators: [withLoadedConfig],
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

type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

/** The page waits on the configuration, so the first wait gets longer than the 1s default. */
const PAGE_LOAD = { timeout: 5000 };

const LABELED_STORAGE = "Apply quota to labeled object stores.";
const DEFAULT_TYPE = "Is this quota a default for a class of users (if yes, what type)?";

/** The control the form field titled `title` labels; a required field's label adds "*" or "* required". */
function field({ canvas }: PlayContext, title: string, role: "textbox" | "combobox" = "textbox") {
    return canvas.getByRole(role, { name: new RegExp(`^${escapeRegExp(title)}( ?\\*( ?required)?)?$`) });
}

/** The whole picker, chosen value and option list included, for the field titled `title`. */
function picker(context: PlayContext, title: string) {
    return field(context, title, "combobox").closest<HTMLElement>('[role="group"]')!;
}

/** Checks the picker for the field titled `title` shows `value` chosen; its closed option list doesn't count. */
async function expectChosen(context: PlayContext, title: string, value: string) {
    const chosen = picker(context, title);
    const options = '[role="option"], [role="option"] *, script, style';
    await expect(await within(chosen).findByText(value, { ignore: options })).toBeVisible();
}

/** Waits for the form card titled `title`, which shows once the form has loaded. */
async function seeForm({ canvas, step }: PlayContext, title: string) {
    await step(`See the form "${title}"`, async () => {
        await expect(await canvas.findByText(title, { selector: "b" }, PAGE_LOAD)).toBeVisible();
    });
}

/** Checks the Groups and Users pickers are shown or not; call after `seeForm`. */
async function seeMemberPickers({ canvas, step }: PlayContext, shown: boolean) {
    await step(shown ? "See the Groups and Users pickers" : "See no Groups or Users pickers", async () => {
        for (const title of ["Groups", "Users"]) {
            if (shown) {
                await expect(canvas.getByText(title, { selector: "span" })).toBeVisible();
            } else {
                await expect(canvas.queryByText(title, { selector: "span" })).not.toBeInTheDocument();
            }
        }
    });
}

/** Clicks Save or Create, and reads the refusal shown above the form. */
async function submitAndSeeRefusal({ canvas, step, userEvent }: PlayContext, button: string, refusal: string) {
    await step(`Click ${button}; the form asks for the missing fields`, async () => {
        await expect(canvas.queryByRole("alert")).not.toBeInTheDocument();
        await userEvent.click(canvas.getByRole("button", { name: button }));
        await expect(await canvas.findByRole("alert")).toHaveTextContent(new RegExp(`^${escapeRegExp(refusal)}$`));
    });
}

/** An empty form for a new quota on a Galaxy with unlabeled storage. Name, description and amount are required. */
export const NewQuota: Story = {
    play: async (context) => {
        await seeForm(context, "Create Quota");
        await context.step("See the name field, and no choice of labeled storage", async () => {
            await expect(field(context, "Name")).toBeVisible();
            await expect(context.canvas.queryByText(LABELED_STORAGE)).not.toBeInTheDocument();
        });
    },

    // TODO a11y: color-contrast, label (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** Creating a quota without a description is refused before anything is sent. */
export const RequiresDescription: Story = {
    play: async (context) => {
        const { step, userEvent } = context;
        await seeForm(context, "Create Quota");
        await step("Fill in the name and amount, but no description", async () => {
            await userEvent.type(field(context, "Name"), "New Quota");
            await userEvent.type(field(context, "Amount"), "10 GB");
        });
        await submitAndSeeRefusal(context, "Create", "Please enter a name, description and amount.");
    },

    // TODO a11y: color-contrast, label (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** A Galaxy whose object stores carry quota labels asks which storage the new quota applies to. */
export const NewQuotaForLabeledStorage: Story = {
    parameters: {
        // TODO a11y: color-contrast, label (2026-10-10 audit).
        a11y: { test: "todo" },
        msw: { handlers: { configuration: configurationHandler({ quota_source_labels: ["scratch"] }) } },
    },
    play: async (context) => {
        await seeForm(context, "Create Quota");
        await context.step("See the labeled storage choice, on the default storage", async () => {
            await expectChosen(context, LABELED_STORAGE, "Default Quota");
        });
    },
};

/** An existing quota with its user and group selected. */
export const ExistingQuota: Story = {
    args: { quotaId: QUOTA.id },
    play: async (context) => {
        const { step } = context;
        await seeForm(context, `Quota '${QUOTA.name}'`);
        await step("Read the quota's name, description and amount", async () => {
            await expect(field(context, "Name")).toHaveValue(QUOTA.name);
            await expect(field(context, "Description")).toHaveValue(QUOTA.description);
            await expect(field(context, "Amount")).toHaveValue(QUOTA.display_amount);
        });
        await seeMemberPickers(context, true);
        await step("See its group and user selected", async () => {
            await expectChosen(context, "Groups", MEMBER_GROUP.name);
            await expectChosen(context, "Users", ADMIN_USER.email);
        });
    },

    // TODO a11y: label, tabindex (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** Renaming the quota leaves the saved name in the form's title until it's saved. */
export const KeepsSavedNameWhileRenaming: Story = {
    args: { ...ExistingQuota.args },
    play: async (context) => {
        const { canvas, step, userEvent } = context;
        await seeForm(context, `Quota '${QUOTA.name}'`);
        await step("Rename the quota; the title keeps the saved name", async () => {
            await userEvent.clear(field(context, "Name"));
            await userEvent.type(field(context, "Name"), "Renamed Quota");
            await expect(field(context, "Name")).toHaveValue("Renamed Quota");
            await expect(canvas.getByText(`Quota '${QUOTA.name}'`, { selector: "b" })).toBeVisible();
            await expect(canvas.queryByText("Quota 'Renamed Quota'")).not.toBeInTheDocument();
        });
    },

    // TODO a11y: label, tabindex (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** Making the quota a default for registered users hides its users and groups, which defaults can't have. */
export const MakesQuotaADefault: Story = {
    args: { ...ExistingQuota.args },
    play: async (context) => {
        const { canvas, step, userEvent } = context;
        await seeForm(context, `Quota '${QUOTA.name}'`);
        await seeMemberPickers(context, true);
        await step('Make it a default for registered users: "Yes, registered"', async () => {
            await expectChosen(context, DEFAULT_TYPE, "No");
            await userEvent.click(picker(context, DEFAULT_TYPE));
            // vue-multiselect listens for clicks on the option's text, not on the option element.
            const option = await canvas.findByRole("option", { name: "Yes, registered" });
            await userEvent.click(within(option).getByText("Yes, registered"));
            await expectChosen(context, DEFAULT_TYPE, "Yes, registered");
        });
        await seeMemberPickers(context, false);
    },

    // TODO a11y: label (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** Clearing the amount is refused before anything is sent. */
export const RequiresNameAndAmount: Story = {
    args: { ...ExistingQuota.args },
    play: async (context) => {
        await seeForm(context, `Quota '${QUOTA.name}'`);
        await context.step("Clear the amount", async () => {
            await context.userEvent.clear(field(context, "Amount"));
        });
        await submitAndSeeRefusal(context, "Save", "Please enter a name and amount.");
    },

    // TODO a11y: label, tabindex (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** The default quota for registered users: it can't have users or groups, so those pickers are hidden. */
export const ExistingDefaultQuota: Story = {
    args: { ...ExistingQuota.args },
    parameters: {
        // TODO a11y: label (2026-10-10 audit).
        a11y: { test: "todo" },
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
    play: async (context) => {
        await seeForm(context, `Quota '${QUOTA.name}'`);
        await context.step('See it is the default for registered users: "Yes, registered"', async () => {
            await expectChosen(context, DEFAULT_TYPE, "Yes, registered");
        });
        await seeMemberPickers(context, false);
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
    play: async ({ canvas, step }) => {
        await step("Read why the quota can't be edited", async () => {
            await expect(await canvas.findByRole("alert", {}, PAGE_LOAD)).toHaveTextContent(
                new RegExp(`^${escapeRegExp(`Quota "${QUOTA.name}" is deleted`)}$`),
            );
        });
        await step("See no form and no Save button", async () => {
            await expect(canvas.queryByRole("textbox")).not.toBeInTheDocument();
            await expect(canvas.queryByRole("button", { name: "Save" })).not.toBeInTheDocument();
        });
    },
};
