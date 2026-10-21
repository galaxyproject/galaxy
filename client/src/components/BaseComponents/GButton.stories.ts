import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { expect, fn, waitFor } from "storybook/test";
import { defineComponent, h, ref } from "vue";

import GButton from "./GButton.vue";

type GButtonArgs = InstanceType<typeof GButton>["$props"] & { label: string };

/**
 * A row that reacts to clicks, as history items and cards do, with a button inside it.
 * The count shows which button clicks reach the row.
 */
export const ClickableRow = defineComponent({
    name: "ClickableRow",
    // Vue 2 compat keeps listeners out of `attrs`; Vue 3 mode forwards `onClick` to the button.
    compatConfig: { MODE: 3 },
    inheritAttrs: false,
    setup(_, { attrs, slots }) {
        const rowClicks = ref(0);

        function onRowClick() {
            rowClicks.value++;
        }

        return () =>
            h(
                "div",
                {
                    "data-description": "clickable row",
                    style: "display: flex; gap: 1rem; align-items: center; padding: 0.5rem; border: 1px solid var(--color-grey-300); cursor: pointer",
                    onClick: onRowClick,
                },
                [
                    h("span", { "data-description": "row clicks" }, `Row clicks: ${rowClicks.value}`),
                    h(GButton, attrs, slots),
                ],
            );
    },
});

const meta = {
    title: "BaseComponents/GButton",
    component: GButton,
    excludeStories: ["ClickableRow"],
    args: { label: "Save", title: "Save your changes", onClick: fn() },
    render:
        ({ label, ...props }) =>
        () =>
            h(GButton, props, () => label),
} satisfies Meta<GButtonArgs>;

export default meta;
type Story = StoryObj<typeof meta>;
type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

/**
 * The name of a button or link labelled `label` whose styled tooltip says `tooltip`.
 *
 * Pre-existing bug, tolerated here: the tooltip renders inside the element, so its text
 * joins the accessible name ("Create page Create a new page") and screen readers read it
 * twice, once as the name and again as the description.
 */
function labelled(label: string, tooltip: string) {
    return new RegExp(`^${label}( ${tooltip})?$`);
}

/**
 * Clicks the button and sees whether it acted: `calls` is how many clicks reach `onClick`.
 * A zero count means something only because `Default` and `ClickReachesRow` show the
 * `onClick` arg reaches the button.
 */
async function clickButton(
    { args, canvas, userEvent, step }: PlayContext,
    label: string,
    calls: 0 | 1,
    name: string | RegExp = label,
) {
    await step(calls ? `Click "${label}"; it acts once` : `Click "${label}"; nothing happens`, async () => {
        await userEvent.click(canvas.getByRole("button", { name }));
        await expect(args.onClick).toHaveBeenCalledTimes(calls);
    });
}

/**
 * The styled tooltip stays in the DOM for screen readers and hides with `sr-only`, which
 * `toBeVisible` can't see, so hovering is checked by that class coming and going. It shows
 * after a hover delay.
 */
async function hoverForTooltip({ canvas, userEvent, step }: PlayContext, element: HTMLElement, text: string) {
    const tooltip = canvas.getByRole("tooltip");
    await step(`Hover to read "${text}" in a tooltip`, async () => {
        await expect(tooltip).toHaveClass("sr-only");
        await userEvent.hover(element);
        await waitFor(() => expect(tooltip).not.toHaveClass("sr-only"));
        await expect(tooltip).toHaveTextContent(new RegExp(`^${text}$`));
        await userEvent.unhover(element);
        await expect(tooltip).toHaveClass("sr-only");
    });
}

/** Tabs to the element and reads its tooltip, which shows on focus without a delay. */
async function tabForTooltip({ canvas, userEvent, step }: PlayContext, element: HTMLElement, text: string) {
    const tooltip = canvas.getByRole("tooltip");
    await step(`Tab to it to read "${text}" in a tooltip`, async () => {
        await userEvent.tab();
        await expect(element).toHaveFocus();
        await waitFor(() => expect(tooltip).not.toHaveClass("sr-only"));
        await expect(tooltip).toHaveTextContent(new RegExp(`^${text}$`));
        element.blur();
        await waitFor(() => expect(tooltip).toHaveClass("sr-only"));
    });
}

/** A plain grey button with a native title. */
export const Default: Story = {
    play: async (context) => {
        await context.step("See the title the browser shows on hover", async () => {
            const button = context.canvas.getByRole("button", { name: "Save" });
            await expect(button).toHaveAttribute("title", "Save your changes");
            await expect(button).toHaveAccessibleDescription("Save your changes");
        });
        await clickButton(context, "Save", 1);
    },
};

/** Unavailable, with a title that says why. It still takes hover so the title can show. */
export const Disabled: Story = {
    args: { disabled: true, disabledTitle: "Nothing to save yet" },
    play: async (context) => {
        await context.step("See it marked unavailable, with the title saying why", async () => {
            const button = context.canvas.getByRole("button", { name: "Save" });
            await expect(button).toHaveAttribute("aria-disabled", "true");
            // A native `disabled` would take the button out of the tab order, so keyboard
            // users couldn't reach the title (`DisabledLink` tabs to its tooltip).
            await expect(button).not.toBeDisabled();
            await expect(button).toHaveAttribute("title", "Nothing to save yet");
            await expect(button).toHaveAccessibleDescription("Nothing to save yet");
        });
        await clickButton(context, "Save", 0);
    },
};

/** Working: a spinner, and clicks are ignored, but the button keeps its colour. */
export const Loading: Story = {
    args: { loading: true, label: "Saving" },
    play: async (context) => {
        await context.step("See it busy, but not unavailable", async () => {
            const button = context.canvas.getByRole("button", { name: "Saving" });
            await expect(button).toHaveAttribute("aria-busy", "true");
            await expect(button).not.toHaveAttribute("aria-disabled");
        });
        await clickButton(context, "Saving", 0);
    },
};

/** A link to another page in Galaxy, with a styled tooltip instead of the native title. */
export const InternalLink: Story = {
    args: { to: "/pages/create", label: "Create page", title: "Create a new page", tooltip: true },
    play: async (context) => {
        const link = context.canvas.getByRole("link", { name: labelled("Create page", "Create a new page") });
        await context.step("See a link to the page, with no native title", async () => {
            await expect(link).toHaveAttribute("href", "/pages/create");
            // RouterLink runs in Vue 3 mode, where a `false` attribute renders as "false".
            await expect(link).not.toHaveAttribute("title");
        });
        await hoverForTooltip(context, link, "Create a new page");
    },
};

/** A disabled link can't be followed, so it's a plain button whose tooltip says why. */
export const DisabledLink: Story = {
    args: { ...InternalLink.args, disabled: true, disabledTitle: "Log in to create pages" },
    play: async (context) => {
        const name = labelled("Create page", "Log in to create pages");
        const button = context.canvas.getByRole("button", { name });
        await context.step("See a button, not a link", async () => {
            await expect(context.canvas.queryByRole("link")).not.toBeInTheDocument();
            await expect(button).toHaveAttribute("aria-disabled", "true");
        });
        await hoverForTooltip(context, button, "Log in to create pages");
        await tabForTooltip(context, button, "Log in to create pages");
        await clickButton(context, "Create page", 0, name);
    },
};

/** A loading link can't be followed either, so it's a plain button too. */
export const LoadingLink: Story = {
    args: { ...InternalLink.args, loading: true },
    play: async (context) => {
        await context.step("See a busy button, not a link", async () => {
            await expect(context.canvas.queryByRole("link")).not.toBeInTheDocument();
            const name = labelled("Create page", "Create a new page");
            await expect(context.canvas.getByRole("button", { name })).toHaveAttribute("aria-busy", "true");
        });
    },
};

/** A link to a URL outside the router, rendered as a plain anchor. */
export const ExternalLink: Story = {
    args: { href: "https://example.org/data.txt", label: "Download", title: "Download the data" },
    play: async ({ canvas, step }) => {
        await step("See a link to the URL as given", async () => {
            await expect(canvas.getByRole("link", { name: "Download" })).toHaveAttribute(
                "href",
                "https://example.org/data.txt",
            );
        });
    },
};

/** A button inside a clickable row: its clicks reach the row only while it's enabled. */
export const InClickableRow: Story = {
    args: { label: "Delete", title: "Delete this item" },
    render:
        ({ label, ...props }) =>
        () =>
            h(ClickableRow, props, () => label),
};

/** The row's count, which goes up for each click that reaches the row. */
async function expectRowClicks({ canvas }: PlayContext, count: number) {
    await expect(canvas.getByText(/^Row clicks: \d+$/)).toHaveTextContent(new RegExp(`^Row clicks: ${count}$`));
}

/** Clicking the enabled button acts, and the click reaches the row too. */
export const ClickReachesRow: Story = {
    ...InClickableRow,
    play: async (context) => {
        await expectRowClicks(context, 0);
        await clickButton(context, "Delete", 1);
        await context.step("See the row count the click", () => expectRowClicks(context, 1));
    },
};

/**
 * Clicking the disabled button does nothing, and the click stops before the row. A native
 * disabled button dispatches no click at all; GButton uses `aria-disabled` instead, so its
 * click guard has to stop the event itself.
 */
export const DisabledClickStopsAtButton: Story = {
    ...InClickableRow,
    args: { ...InClickableRow.args, disabled: true, disabledTitle: "This item is in use" },
    play: async (context) => {
        await expectRowClicks(context, 0);
        await clickButton(context, "Delete", 0);
        await context.step("See the row count no click", () => expectRowClicks(context, 0));
    },
};
