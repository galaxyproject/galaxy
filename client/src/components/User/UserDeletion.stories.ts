import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeRegisteredUser } from "@tests/test-data";
import { withCurrentUser } from "@tests/test-data/currentUser";

import { http } from "@/api/client/__mocks__/http";

import UserDeletion from "./UserDeletion.vue";

const SIGNED_IN_USER = getFakeRegisteredUser({ id: "f2db41e1fa331b3e", email: "alice@example.org" });

const meta = {
    title: "User/UserDeletion",
    component: UserDeletion,
    // The dialog opens from the user's preferences, so someone is signed in.
    decorators: [withCurrentUser(() => SIGNED_IN_USER)],
    parameters: {
        msw: {
            handlers: {
                deleteUser: http.delete("/api/users/{user_id}", ({ response }) =>
                    response(200).json({ ...SIGNED_IN_USER, deleted: true }),
                ),
            },
        },
    },
} satisfies Meta<typeof UserDeletion>;

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Waiting for the user to confirm by typing their email, which enables the delete button. Once
 * deleted, Galaxy logs them out.
 */
export const AwaitingConfirmation: Story = {};

/** This Galaxy isn't configured to allow account deletion (the default), so deleting shows an error inside the dialog. */
export const SelfDeletionNotAllowed: Story = {
    parameters: {
        msw: {
            handlers: {
                deleteUser: http.delete("/api/users/{user_id}", ({ response }) =>
                    response("4XX").json(
                        {
                            err_msg: "The configuration of this Galaxy instance does not allow admins to delete users.",
                            err_code: 403004,
                        },
                        { status: 403 },
                    ),
                ),
            },
        },
    },
};
