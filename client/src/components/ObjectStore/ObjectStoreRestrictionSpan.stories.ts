import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { expect, screen } from "storybook/test";

import { escapeRegExp } from "@/utils/regExp";

import ObjectStoreRestrictionSpan from "./ObjectStoreRestrictionSpan.vue";

const meta = {
    title: "ObjectStore/ObjectStoreRestrictionSpan",
    component: ObjectStoreRestrictionSpan,
} satisfies Meta<typeof ObjectStoreRestrictionSpan>;

export default meta;
type Story = StoryObj<typeof meta>;

type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

/** Reads the storage label, then hovers it to read the whole explanation in its tooltip. */
function labelsAndExplains(label: string, explanation: string) {
    return async ({ canvas, step, userEvent }: PlayContext) => {
        let shown!: HTMLElement;
        await step(`See the storage labelled "${label}"`, async () => {
            shown = canvas.getByText(label);
            await expect(shown).toBeVisible();
        });
        await step("Hover the label to read what it means", async () => {
            await expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
            await userEvent.hover(shown);
            await expect(await screen.findByRole("tooltip")).toHaveTextContent(
                new RegExp(`^${escapeRegExp(explanation)}$`),
            );
            await expect(shown).toHaveAccessibleDescription(explanation);
            await userEvent.unhover(shown);
            await expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
        });
    };
}

/** Storage restricted to one user: its datasets can't be shared, published or added to libraries. */
export const Private: Story = {
    args: { isPrivate: true },
    play: labelsAndExplains(
        "private",
        "This dataset is stored on storage restricted to a single user. It cannot be shared, published, or added to Galaxy data libraries.",
    ),
};

/** Storage that allows Galaxy's usual sharing, publishing and library features. */
export const Sharable: Story = {
    args: { isPrivate: false },
    play: labelsAndExplains(
        "sharable",
        "This dataset is stored on storage that allows standard Galaxy sharing features. If you have sufficient Galaxy permissions to this dataset - the dataset can be published, shared, or added to data libraries within Galaxy.",
    ),
};
