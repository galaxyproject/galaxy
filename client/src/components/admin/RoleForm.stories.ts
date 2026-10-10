import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { expect, waitFor, within } from "storybook/test";

import { http } from "@/api/client/__mocks__/http";
import { escapeRegExp } from "@/utils/regExp";

import { ADMIN_GROUPS, ADMIN_USER, adminGroups, adminUserSearch } from "./test_fixtures";

import RoleForm from "./RoleForm.vue";

const ROLE = {
    id: "5f1e3a6c7d2b9e04",
    name: "Data managers",
    description: "Can run data manager tools",
    type: "admin",
    url: "/api/roles/5f1e3a6c7d2b9e04",
    model_class: "Role" as const,
};
const ROLE_MEMBER = { id: ADMIN_USER.id, email: ADMIN_USER.email };
const ROLE_GROUP = ADMIN_GROUPS[0]!;

/** Galaxy's answer when another role already has the name. */
function nameTaken(name: string) {
    return { err_msg: `A role with that name already exists [${name}]`, err_code: 409001 };
}

const meta = {
    title: "admin/RoleForm",
    component: RoleForm,
    parameters: {
        msw: {
            handlers: {
                groups: adminGroups(),
                userSearch: adminUserSearch(),
                createRole: http.post("/api/roles", async ({ request, response }) => {
                    const { name, description } = await request.json();
                    return response(200).json({ ...ROLE, name, description });
                }),
                role: http.get("/api/roles/{id}", ({ response }) => response(200).json(ROLE)),
                roleUsers: http.get("/api/roles/{id}/users", ({ response }) => response(200).json([ROLE_MEMBER])),
                roleGroups: http.get("/api/roles/{id}/groups", ({ response }) =>
                    response(200).json([{ id: ROLE_GROUP.id, name: ROLE_GROUP.name, model_class: "Group" }]),
                ),
                updateRole: http.put("/api/roles/{id}", ({ response }) => response(200).json(ROLE)),
            },
        },
    },
} satisfies Meta<typeof RoleForm>;

export default meta;
type Story = StoryObj<typeof meta>;
type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

/** The form shows once Galaxy answers, so the first wait gets longer than the 1s default. */
const PAGE_LOAD = { timeout: 5000 };

/** The control the form field titled `title` labels; a required field's label adds "*" or "* required". */
function field({ canvas }: PlayContext, title: string, role: "textbox" | "combobox" = "textbox") {
    return canvas.getByRole(role, { name: new RegExp(`^${escapeRegExp(title)}( ?\\*( ?required)?)?$`) });
}

/** The whole picker, chosen tags and option list included, for the field titled `title`. */
function picker(context: PlayContext, title: string) {
    return field(context, title, "combobox").closest<HTMLElement>('[role="group"]')!;
}

/** Checks the closed picker for the field titled `title` shows only `value` chosen. */
async function expectOnlyChosen(context: PlayContext, title: string, value: string) {
    const chosen = picker(context, title);
    await expect(await within(chosen).findByText(value)).toBeVisible();
    await expect(chosen).toHaveTextContent(new RegExp(`^${escapeRegExp(value)}$`));
}

/** Waits for the form card titled `title`, which shows once the form has loaded. */
async function seeForm({ canvas, step }: PlayContext, title: string) {
    await step(`See the form "${title}"`, async () => {
        await expect(await canvas.findByText(title, { selector: "b" }, PAGE_LOAD)).toBeVisible();
    });
}

/** Reads the whole alert shown above the form; `button` is the save button, if the alert follows a click on it. */
async function seeAlert({ canvas, step, userEvent }: PlayContext, text: string, button?: string) {
    const exactly = new RegExp(`^${escapeRegExp(text)}$`);
    if (button) {
        await step(`Click ${button}; see "${text}"`, async () => {
            await expect(canvas.queryByRole("alert")).not.toBeInTheDocument();
            await userEvent.click(canvas.getByRole("button", { name: button }));
            await expect(await canvas.findByRole("alert")).toHaveTextContent(exactly);
        });
    } else {
        await step(`See "${text}"`, async () => {
            await expect(await canvas.findByRole("alert", {}, PAGE_LOAD)).toHaveTextContent(exactly);
        });
    }
}

/** Checks the form and its save button are gone; call after the alert that says why. */
async function seeNoForm({ canvas, step }: PlayContext) {
    await step("See no form and no save button", async () => {
        await expect(canvas.queryByRole("textbox")).not.toBeInTheDocument();
        await expect(canvas.queryByRole("button", { name: /^(Create|Save)$/ })).not.toBeInTheDocument();
    });
}

/** Fills in a new role's name and description. */
async function describeRole(context: PlayContext, name: string) {
    await context.step(`Name the role "${name}" and describe it`, async () => {
        await context.userEvent.type(field(context, "Name"), name);
        await context.userEvent.type(field(context, "Description"), "Test Description");
    });
}

/** An empty form for a new role, offering every group. Name, description and type are required. */
export const NewRole: Story = {
    // TODO a11y: color-contrast, label (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** Answers the groups request held by `groupsHeld`; the play sets it when the request arrives. */
let answerHeldGroups: (() => void) | undefined;

/** Galaxy takes the groups request but holds its answer until the play calls `answerHeldGroups`. */
const groupsHeld = http.get("/api/groups", async ({ response }) => {
    await new Promise<void>((resolve) => {
        answerHeldGroups = resolve;
    });
    return response(200).json(ADMIN_GROUPS);
});

/** The form waits for the groups it offers before it shows. */
export const WaitsForGroups: Story = {
    parameters: {
        // TODO a11y: color-contrast, label (2026-10-10 audit).
        a11y: { test: "todo" },
        msw: { handlers: { groups: groupsHeld } },
    },
    // A run that stopped before releasing the request leaves its answer behind; drop it and answer it.
    beforeEach: () => {
        answerHeldGroups = undefined;
        return () => answerHeldGroups?.();
    },
    play: async ({ canvas, step }) => {
        await step("See the page loading while Galaxy sends the groups", async () => {
            await waitFor(() => expect(answerHeldGroups).toBeDefined(), PAGE_LOAD);
            await expect(canvas.getByText("Loading...")).toBeVisible();
            await expect(canvas.queryByRole("button", { name: "Create" })).not.toBeInTheDocument();
        });
        await step("Galaxy answers; see the form and its Create button", async () => {
            answerHeldGroups?.();
            answerHeldGroups = undefined;
            await expect(await canvas.findByRole("button", { name: "Create" })).toBeVisible();
            await expect(canvas.queryByText("Loading...")).not.toBeInTheDocument();
        });
    },
};

/** A new role without a description is refused before anything is sent. */
export const RequiresNameAndDescription: Story = {
    play: async (context) => {
        await seeForm(context, "Create a new Role");
        await seeAlert(context, "Please complete all required inputs.", "Create");
    },

    // TODO a11y: color-contrast, label (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** Typing three letters of an email into the Users picker offers the users it matches. */
export const SearchesUsersByEmail: Story = {
    play: async (context) => {
        const { canvas, step, userEvent } = context;
        await seeForm(context, "Create a new Role");
        await step("Open the Users picker; it asks for an email to search", async () => {
            await userEvent.click(picker(context, "Users"));
            // The picker keeps its "no options" and "no results" notes in the DOM and shows one.
            const notes = await within(picker(context, "Users")).findAllByText("Enter at least 3 characters to search");
            await expect(notes.filter((note) => note.checkVisibility())).toHaveLength(1);
            await expect(canvas.queryByRole("option", { name: ADMIN_USER.email })).not.toBeInTheDocument();
        });
        await step(`Type "alice"; see ${ADMIN_USER.email} offered`, async () => {
            await userEvent.keyboard("alice");
            const option = await canvas.findByRole("option", { name: ADMIN_USER.email });
            // The option list fades in.
            await waitFor(() => expect(option).toBeVisible());
        });
    },

    // TODO a11y: aria-required-attr, color-contrast, label (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** The groups can't be loaded, so the form isn't shown and nothing can be created. */
export const GroupsFailToLoad: Story = {
    parameters: {
        msw: {
            handlers: {
                groups: http.get("/api/groups", ({ response }) =>
                    response("5XX").json({ err_msg: "Internal server error.", err_code: 500001 }, { status: 500 }),
                ),
            },
        },
    },
    play: async (context) => {
        await seeAlert(context, "Internal server error.");
        await seeNoForm(context);
    },
};

/** Another role already has the name typed in, so creating shows Galaxy's refusal above the form. */
export const NewRoleNameTaken: Story = {
    parameters: {
        // TODO a11y: color-contrast, label (2026-10-10 audit).
        a11y: { test: "todo" },
        msw: {
            handlers: {
                createRole: http.post("/api/roles", async ({ request, response }) =>
                    response("4XX").json(nameTaken((await request.json()).name), { status: 409 }),
                ),
            },
        },
    },
    play: async (context) => {
        await seeForm(context, "Create a new Role");
        await describeRole(context, ROLE.name);
        await seeAlert(context, `Failed to create role: ${nameTaken(ROLE.name).err_msg}`, "Create");
    },
};

/** An existing role, with its member and group selected. Its type can't change. */
export const ExistingRole: Story = {
    args: { roleId: ROLE.id },
    play: async (context) => {
        const { canvas, step } = context;
        await seeForm(context, `Role '${ROLE.name}'`);
        await step("Read the role's name and description", async () => {
            await expect(field(context, "Name")).toHaveValue(ROLE.name);
            await expect(field(context, "Description")).toHaveValue(ROLE.description);
        });
        await step("See its group and member chosen", async () => {
            await expectOnlyChosen(context, "Groups", ROLE_GROUP.name);
            await expectOnlyChosen(context, "Users", ROLE_MEMBER.email);
        });
        await step("See no choice of role type", async () => {
            await expect(canvas.queryByText("Role Type", { selector: "span" })).not.toBeInTheDocument();
        });
    },

    // TODO a11y: label, tabindex (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** Renaming the role leaves the saved name in the form's title until it's saved. */
export const KeepsSavedNameWhileRenaming: Story = {
    args: { ...ExistingRole.args },
    play: async (context) => {
        const { canvas, step, userEvent } = context;
        await seeForm(context, `Role '${ROLE.name}'`);
        await step("Rename the role; the title keeps the saved name", async () => {
            await userEvent.clear(field(context, "Name"));
            await userEvent.type(field(context, "Name"), "Renamed Role");
            await expect(field(context, "Name")).toHaveValue("Renamed Role");
            await expect(canvas.getByText(`Role '${ROLE.name}'`, { selector: "b" })).toBeVisible();
            await expect(canvas.queryByText("Role 'Renamed Role'")).not.toBeInTheDocument();
        });
    },

    // TODO a11y: label, tabindex (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** The role was deleted while its members loaded; saving would drop them, so the form isn't shown. */
export const ExistingRoleGone: Story = {
    args: { ...ExistingRole.args },
    parameters: {
        msw: {
            handlers: {
                roleUsers: http.get("/api/roles/{id}/users", ({ response }) =>
                    response("4XX").json(
                        { err_msg: "No accessible role found with the id provided.", err_code: 404001 },
                        { status: 404 },
                    ),
                ),
            },
        },
    },
    play: async (context) => {
        await seeAlert(context, "No accessible role found with the id provided.");
        await seeNoForm(context);
    },
};

/** Another role already has the new name, so saving shows Galaxy's refusal above the form. */
export const ExistingRoleNameTaken: Story = {
    args: { ...ExistingRole.args },
    parameters: {
        // TODO a11y: label, tabindex (2026-10-10 audit).
        a11y: { test: "todo" },
        msw: {
            handlers: {
                updateRole: http.put("/api/roles/{id}", async ({ request, response }) =>
                    response("4XX").json(nameTaken((await request.json()).name ?? ""), { status: 409 }),
                ),
            },
        },
    },
    play: async (context) => {
        await seeForm(context, `Role '${ROLE.name}'`);
        await context.step('Rename the role "Teaching assistants"', async () => {
            await context.userEvent.clear(field(context, "Name"));
            await context.userEvent.type(field(context, "Name"), "Teaching assistants");
        });
        await seeAlert(context, `Failed to update role: ${nameTaken("Teaching assistants").err_msg}`, "Save");
    },
};
