import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { HttpResponse } from "msw";

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

/** Opened from the emailed reset link (`/login/start?token=…`): only the new password is asked for. */
export const ResetFromEmailLink: Story = {
    args: { token: "9b2f4c7e1a8d3f60b5e2c9a4d7f1e3b8" },
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
};

/** The reset link was already used or has expired, so saving shows Galaxy's reason in a danger alert. */
export const ResetLinkExpired: Story = {
    args: { ...ResetFromEmailLink.args },
    parameters: {
        msw: {
            handlers: {
                // The legacy controller answers a rejected change with a 400 and the reason.
                changePassword: http.untyped.post("/user/change_password", () =>
                    HttpResponse.json(
                        { err_msg: "Invalid or expired password reset token, please request a new one." },
                        { status: 400 },
                    ),
                ),
            },
        },
    },
};
