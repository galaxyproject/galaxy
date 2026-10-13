import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { expect, within } from "storybook/test";

import TextSummary from "./TextSummary.vue";

const meta = {
    title: "Common/TextSummary",
    component: TextSummary,
    args: {
        description: "Trimmed <b>paired</b> reads",
    },
} satisfies Meta<typeof TextSummary>;

export default meta;
type Story = StoryObj<typeof meta>;

/** A history annotation: markup in it shows as literal text. */
export const PlainText: Story = {
    play: async ({ canvasElement, step }) => {
        const canvas = within(canvasElement);
        await step("Show the annotation's markup as literal text", async () => {
            expect(canvas.getByText("Trimmed <b>paired</b> reads", { exact: true })).toBeVisible();
            expect(canvas.queryByText("paired", { exact: true })).toBeNull();
        });
    },
};

/** Finds the description's bold word and checks it rendered as `<b>`. */
async function findRenderedBold(canvasElement: HTMLElement) {
    const bold = await within(canvasElement).findByText("paired", { exact: true });
    expect(bold).toBeVisible();
    expect(bold.tagName).toBe("B");
    return bold;
}

/** A workflow annotation, which callers opt into rendering as sanitized HTML. */
export const RenderedHtml: Story = {
    args: { isHtml: true },
    play: async ({ canvasElement, step }) => {
        await step("Render the annotation's markup", async () => {
            const bold = await findRenderedBold(canvasElement);
            expect(bold.parentElement).toHaveTextContent(/^Trimmed paired reads$/);
        });
    },
};

/** Rendered HTML keeps the text of form controls but not the controls themselves. */
export const DropsFormControls: Story = {
    args: { isHtml: true, description: "Trimmed <b>paired</b> reads <button>Delete history</button>" },
    play: async ({ canvasElement, step }) => {
        await step("Show the button's text without a button", async () => {
            const bold = await findRenderedBold(canvasElement);
            expect(bold.parentElement).toHaveTextContent(/^Trimmed paired reads Delete history$/);
            expect(within(canvasElement).queryByRole("button")).toBeNull();
        });
    },
};
