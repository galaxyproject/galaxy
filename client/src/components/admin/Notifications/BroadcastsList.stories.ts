import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { expect, waitFor } from "storybook/test";

import { http } from "@/api/client/__mocks__/http";
import { broadcast, type BroadcastScenario, DAY, HOUR } from "@/components/Notifications/Broadcasts/test_fixtures";
import { escapeRegExp } from "@/utils/regExp";

import BroadcastsList from "./BroadcastsList.vue";

const ONE_OF_EACH: BroadcastScenario[] = [
    {
        id: "a7c1ee54b2d8f390",
        variant: "info",
        subject: "Galaxy 26.1 is live",
        message: "See the **release notes** for what's new.",
        publishedIn: -2 * HOUR,
        expiresIn: 5 * DAY,
    },
    {
        id: "5f2b9d0c3e6a1847",
        variant: "warning",
        subject: "Maintenance on Saturday",
        message: "Jobs queued during the window will start once it ends.",
        publishedIn: 2 * DAY,
        expiresIn: 3 * DAY,
    },
    {
        id: "c39e8a7d1b40f256",
        variant: "urgent",
        subject: "Storage outage resolved",
        message: "Uploads work again.",
        publishedIn: -3 * DAY,
        expiresIn: -1 * DAY,
    },
];

/** Answers the admin's request for every broadcast, timed from the moment of the request. */
function allBroadcasts(scenarios: BroadcastScenario[]) {
    return http.get("/api/notifications/broadcast", ({ response }) => {
        const now = Date.now();
        return response(200).json(scenarios.map((scenario) => broadcast(now, scenario)));
    });
}

const meta = {
    title: "admin/Notifications/BroadcastsList",
    component: BroadcastsList,
    parameters: { msw: { handlers: { broadcasts: allBroadcasts(ONE_OF_EACH) } } },
} satisfies Meta<typeof BroadcastsList>;

export default meta;
type Story = StoryObj<typeof meta>;

type PlayContext = Parameters<NonNullable<Story["play"]>>[0];
type Canvas = PlayContext["canvas"];

const ACTIVE = "Galaxy 26.1 is live";
const SCHEDULED = "Maintenance on Saturday";
const EXPIRED = "Storage outage resolved";

const NOTHING_TO_SHOW =
    "There are no broadcast notifications to show. Use the button above to create a new broadcast notification or change the filters.";

/** The listed broadcasts' subjects, in the order shown; each card's subject is a level-1 heading. */
function shownSubjects(canvas: Canvas) {
    return canvas.queryAllByRole("heading", { level: 1 }).map((heading) => heading.textContent?.trim());
}

async function expectShown(canvas: Canvas, subjects: string[]) {
    await waitFor(() => expect(shownSubjects(canvas)).toEqual(subjects));
}

async function toggleFilters({ canvas, userEvent }: PlayContext, ...filters: ("Active" | "Scheduled" | "Expired")[]) {
    for (const filter of filters) {
        await userEvent.click(canvas.getByRole("button", { name: filter }));
    }
}

async function seeEveryBroadcast({ canvas, step }: PlayContext) {
    await step("See every broadcast, newest first, with every filter on", async () => {
        await canvas.findAllByRole("heading", { level: 1 }, { timeout: 5000 });
        await expectShown(canvas, [SCHEDULED, ACTIVE, EXPIRED]);
        await expect(canvas.queryByText(NOTHING_TO_SHOW)).not.toBeInTheDocument();
        await expect(canvas.queryByRole("status")).not.toBeInTheDocument();
    });
}

/** An active, a scheduled and an expired broadcast, newest first. */
export const OneOfEach: Story = {
    play: seeEveryBroadcast,
};

/** No broadcasts yet, so the list says how to create one. */
export const NoBroadcasts: Story = {
    parameters: { msw: { handlers: { broadcasts: allBroadcasts([]) } } },
    play: async ({ canvas, step }) => {
        await step("Read that there is nothing to show", async () => {
            const note = await canvas.findByText(NOTHING_TO_SHOW, {}, { timeout: 5000 });
            await expect(note).toBeVisible();
            await expect(canvas.getByRole("status")).toHaveTextContent(
                new RegExp(`^${escapeRegExp(NOTHING_TO_SHOW)}$`),
            );
            await expect(shownSubjects(canvas)).toEqual([]);
        });
    },
};

/** Each filter alone lists only the broadcasts in its state. */
export const FiltersByState: Story = {
    play: async (context) => {
        const { canvas, step } = context;
        await seeEveryBroadcast(context);
        await step("Turn off Scheduled and Expired to list only the active broadcast", async () => {
            await toggleFilters(context, "Scheduled", "Expired");
            await expectShown(canvas, [ACTIVE]);
        });
        await step("Swap Active for Scheduled to list only the scheduled broadcast", async () => {
            await toggleFilters(context, "Scheduled", "Active");
            await expectShown(canvas, [SCHEDULED]);
        });
        await step("Swap Scheduled for Expired to list only the expired broadcast", async () => {
            await toggleFilters(context, "Expired", "Scheduled");
            await expectShown(canvas, [EXPIRED]);
        });
    },
};

/** With every filter off the list says there is nothing to show; switching filters back on lists their broadcasts again. */
export const TogglesEveryFilter: Story = {
    play: async (context) => {
        const { canvas, step } = context;
        await seeEveryBroadcast(context);
        await step("Turn every filter off and read that there is nothing to show", async () => {
            await toggleFilters(context, "Active", "Scheduled", "Expired");
            await expect(await canvas.findByText(NOTHING_TO_SHOW)).toBeVisible();
            await expect(shownSubjects(canvas)).toEqual([]);
        });
        await step("Turn Active back on to list the active broadcast", async () => {
            await toggleFilters(context, "Active");
            await expectShown(canvas, [ACTIVE]);
            await expect(canvas.queryByText(NOTHING_TO_SHOW)).not.toBeInTheDocument();
        });
        await step("Turn Scheduled back on to add the scheduled broadcast", async () => {
            await toggleFilters(context, "Scheduled");
            await expectShown(canvas, [SCHEDULED, ACTIVE]);
        });
        await step("Turn Expired back on to list every broadcast again", async () => {
            await toggleFilters(context, "Expired");
            await expectShown(canvas, [SCHEDULED, ACTIVE, EXPIRED]);
        });
    },
};
