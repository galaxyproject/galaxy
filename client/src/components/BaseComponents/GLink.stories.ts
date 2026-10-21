import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { expect, fn, waitFor } from "storybook/test";
import { defineComponent, h, ref } from "vue";

import GLink from "./GLink.vue";

type GLinkArgs = InstanceType<typeof GLink>["$props"] & { label: string };

/**
 * A row that reacts to clicks, as history items and cards do, with a link inside it.
 * The count shows which link clicks reach the row.
 */
export const ClickableRow = defineComponent({
    name: "ClickableRow",
    // Vue 2 compat keeps listeners out of `attrs`; Vue 3 mode forwards `onClick` to the link.
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
                    h(GLink, attrs, slots),
                ],
            );
    },
});

const meta = {
    title: "BaseComponents/GLink",
    component: GLink,
    excludeStories: ["ClickableRow"],
    args: { label: "Show details", onClick: fn() },
    render:
        ({ label, ...props }) =>
        () =>
            h(GLink, props, () => label),
} satisfies Meta<GLinkArgs>;

export default meta;
type Story = StoryObj<typeof meta>;
type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

/**
 * The name of a link labelled `label` whose styled tooltip says `tooltip`.
 *
 * Pre-existing bug, tolerated here: the tooltip renders inside the link, so its text joins
 * the accessible name ("Create a page Create a new page"); see `GButton.stories.ts`.
 */
function labelled(label: string, tooltip: string) {
    return new RegExp(`^${label}( ${tooltip})?$`);
}

/**
 * Clicks `element` and sees whether it acted: `calls` is how many clicks reach `onClick`.
 * A zero count means something only because `InlineButton` and `ClickReachesRow` show the
 * `onClick` arg reaches the link.
 */
async function clickLink({ args, userEvent, step }: PlayContext, element: HTMLElement, label: string, calls: 0 | 1) {
    await step(calls ? `Click "${label}"; it acts once` : `Click "${label}"; nothing happens`, async () => {
        await userEvent.click(element);
        await expect(args.onClick).toHaveBeenCalledTimes(calls);
    });
}

/** Inline text that acts as a button, with no place to go. */
export const InlineButton: Story = {
    play: async (context) => {
        await clickLink(context, context.canvas.getByRole("button", { name: "Show details" }), "Show details", 1);
    },
};

/** A link to another page in Galaxy, with a styled tooltip instead of the native title. */
export const InternalLink: Story = {
    args: { to: "/pages/create", label: "Create a page", title: "Create a new page", tooltip: true },
    play: async (context) => {
        const { canvas, userEvent, step } = context;
        const link = canvas.getByRole("link", { name: labelled("Create a page", "Create a new page") });
        await step("See an available link to the page, with no native title", async () => {
            await expect(link).toHaveAttribute("href", "/pages/create");
            // Vue 3 renders `aria-disabled="false"` for a bound false, which breaks
            // `:not([aria-disabled])` selectors.
            await expect(link).not.toHaveAttribute("aria-disabled");
            // RouterLink runs in Vue 3 mode, where a `false` attribute renders as "false".
            await expect(link).not.toHaveAttribute("title");
        });
        // The styled tooltip stays in the DOM for screen readers and hides with `sr-only`.
        const tooltip = canvas.getByRole("tooltip");
        await step('Hover to read "Create a new page" in a tooltip', async () => {
            await expect(tooltip).toHaveClass("sr-only");
            await userEvent.hover(link);
            await waitFor(() => expect(tooltip).not.toHaveClass("sr-only"));
            await expect(tooltip).toHaveTextContent(/^Create a new page$/);
            await userEvent.unhover(link);
            await expect(tooltip).toHaveClass("sr-only");
        });
        // The listener reaches RouterLink's anchor by fallthrough, beside its navigation handler.
        await clickLink(context, link, "Create a page", 1);
    },
};

/** A link to a URL outside the router, rendered as a plain anchor. */
export const ExternalLink: Story = {
    args: { href: "https://example.org/data.txt", label: "data.txt" },
    play: async ({ canvas, step }) => {
        await step("See an available link to the URL as given", async () => {
            const link = canvas.getByRole("link", { name: "data.txt" });
            await expect(link).toHaveAttribute("href", "https://example.org/data.txt");
            await expect(link).not.toHaveAttribute("aria-disabled");
        });
    },
};

/** Unavailable: greyed out, no href to follow, clicks go nowhere, and the title says why. */
export const Disabled: Story = {
    args: {
        href: "https://example.org/data.txt",
        label: "data.txt",
        title: "Download data.txt",
        disabled: true,
        disabledTitle: "The upload hasn't finished yet",
    },
    play: async (context) => {
        const { canvas, step } = context;
        const button = canvas.getByRole("button", { name: "data.txt" });
        await step("See a button with nowhere to go, marked unavailable, with the title saying why", async () => {
            await expect(canvas.queryByRole("link")).not.toBeInTheDocument();
            await expect(button).not.toHaveAttribute("href");
            await expect(button).toHaveAttribute("aria-disabled", "true");
            await expect(button).toHaveAttribute("title", "The upload hasn't finished yet");
            await expect(button).toHaveAccessibleDescription("The upload hasn't finished yet");
        });
        await clickLink(context, button, "data.txt", 0);
    },
};

/** A link inside a clickable row: its clicks reach the row only while it's enabled. */
export const InClickableRow: Story = {
    args: { href: "https://example.org/data.txt", label: "data.txt" },
    render:
        ({ label, ...props }) =>
        () =>
            h(ClickableRow, props, () => label),
};

/** The row's count, which goes up for each click that reaches the row. */
async function expectRowClicks({ canvas }: PlayContext, count: number) {
    await expect(canvas.getByText(/^Row clicks: \d+$/)).toHaveTextContent(new RegExp(`^Row clicks: ${count}$`));
}

/**
 * Clicking an enabled link acts, and the click reaches the row too. It links within Galaxy:
 * clicking `InClickableRow`'s external anchor would navigate Storybook away.
 */
export const ClickReachesRow: Story = {
    ...InClickableRow,
    args: { to: "/pages/create", label: "Create a page" },
    play: async (context) => {
        await expectRowClicks(context, 0);
        await clickLink(context, context.canvas.getByRole("link", { name: "Create a page" }), "Create a page", 1);
        await context.step("See the row count the click", () => expectRowClicks(context, 1));
    },
};

/**
 * Clicking a disabled link does nothing, and the click stops before the row. A native
 * disabled button dispatches no click at all; GLink uses `aria-disabled` instead, so its
 * click guard has to stop the event itself.
 */
export const DisabledClickStopsAtLink: Story = {
    ...InClickableRow,
    args: { ...InClickableRow.args, disabled: true },
    play: async (context) => {
        await expectRowClicks(context, 0);
        await clickLink(context, context.canvas.getByRole("button", { name: "data.txt" }), "data.txt", 0);
        await context.step("See the row count no click", () => expectRowClicks(context, 0));
    },
};
