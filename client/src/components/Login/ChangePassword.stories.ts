import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { exactly } from "@tests/test-data/text";
import { HttpResponse } from "msw";
import { expect } from "storybook/test";

import { http } from "@/api/client/__mocks__/http";

import ChangePassword from "./ChangePassword.vue";

const meta = {
    title: "Login/ChangePassword",
    component: ChangePassword,
    parameters: {
        msw: {
            handlers: {
                // Not under /api/, so without a handler Storybook would send it to the network.
                changePassword: http.untyped.post("/user/change_password", () => HttpResponse.json({})),
            },
        },
    },
} satisfies Meta<typeof ChangePassword>;

export default meta;
type Story = StoryObj<typeof meta>;

type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

const REFUSED = "Invalid or expired password reset token, please request a new one.";

/** Checks the card's title and its password fields, in order, each a masked input named by its label. */
async function seePasswordFields({ canvas, canvasElement, step }: PlayContext, fields: string[]) {
    await step(`See the "Change your password" card asking for: ${fields.join(", ")}`, async () => {
        await expect(canvas.getByText(exactly("Change your password"))).toBeVisible();
        const inputs = Array.from(canvasElement.querySelectorAll("input"));
        await expect(inputs.map((input) => input.labels?.[0]?.textContent?.trim())).toEqual(fields);
        for (const [index, field] of fields.entries()) {
            const input = canvas.getByLabelText(exactly(field));
            await expect(input).toBe(inputs[index]);
            await expect(input).toHaveAttribute("type", "password");
            await expect(input).toBeVisible();
        }
        await expect(canvas.getByRole("button", { name: "Save new password" })).toBeVisible();
    });
}

/** Opened from the emailed reset link (`/login/start?token=…`): only the new password is asked for. */
export const ResetFromEmailLink: Story = {
    args: { token: "9b2f4c7e1a8d3f60b5e2c9a4d7f1e3b8" },
    play: async (context) => {
        await seePasswordFields(context, ["New Password", "Confirm password"]);
        await context.step("See no message", async () => {
            await expect(context.canvas.queryByRole("alert")).not.toBeInTheDocument();
            await expect(context.canvas.queryByRole("status")).not.toBeInTheDocument();
        });
    },

    // TODO a11y: label (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/**
 * Login refused an expired password, so the current one is asked for as well. The message is
 * the login response's; LoginForm shows it in a browser alert and doesn't forward it yet.
 */
export const PasswordExpired: Story = {
    args: {
        expiredUser: "f2db41e1fa331b3e",
        messageText: "Your password has expired. Please reset or change it to access Galaxy.",
        messageVariant: "warning",
    },
    play: async (context) => {
        await context.step("See the message login gave", async () => {
            await expect(context.canvas.getByRole("alert")).toHaveTextContent(
                exactly("Your password has expired. Please reset or change it to access Galaxy."),
            );
        });
        await seePasswordFields(context, ["Current Password", "New Password", "Confirm password"]);
    },

    // TODO a11y: label (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** The reset link was already used or has expired, so saving shows Galaxy's reason in a danger alert. */
export const ResetLinkExpired: Story = {
    args: { ...ResetFromEmailLink.args },
    parameters: {
        // TODO a11y: label (2026-10-10 audit).
        a11y: { test: "todo" },
        msw: {
            handlers: {
                // The legacy controller answers a rejected change with a 400 and the reason.
                changePassword: http.untyped.post("/user/change_password", () =>
                    HttpResponse.json({ err_msg: REFUSED }, { status: 400 }),
                ),
            },
        },
    },
};

/** Saving with a used or expired reset link shows Galaxy's reason above the form, which stays. */
export const ShowsWhyResetFailed: Story = {
    ...ResetLinkExpired,
    play: async (context) => {
        const { canvas, step, userEvent } = context;
        await seePasswordFields(context, ["New Password", "Confirm password"]);
        await step(`Save; see "${REFUSED}"`, async () => {
            await expect(canvas.queryByRole("alert")).not.toBeInTheDocument();
            await userEvent.click(canvas.getByRole("button", { name: "Save new password" }));
            await expect(await canvas.findByRole("alert")).toHaveTextContent(exactly(REFUSED));
        });
        await seePasswordFields(context, ["New Password", "Confirm password"]);
    },
};
