import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { expect, waitFor, within } from "storybook/test";

import { http } from "@/api/client/__mocks__/http";
import type { TourSummary } from "@/api/tours";

import { CORE_TOURS, RNA_SEQ_TOUR } from "./test_fixtures";

import TourList from "./TourList.vue";

/** Answers `/api/tours` with `tours`. */
function tourList(tours: TourSummary[]) {
    return http.get("/api/tours", ({ response }) => response(200).json(tours));
}

const meta = {
    title: "Tour/TourList",
    component: TourList,
} satisfies Meta<typeof TourList>;

export default meta;
type Story = StoryObj<typeof meta>;
type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

async function seeTours({ canvas }: PlayContext, tours: TourSummary[]) {
    await waitFor(() => expect(canvas.getAllByRole("link")).toHaveLength(tours.length), { timeout: 5000 });
    const links = canvas.getAllByRole("link");
    for (const [index, tour] of tours.entries()) {
        const link = links[index]!;
        await expect(within(link).getByText(tour.name || tour.id, { exact: true })).toBeVisible();
        await expect(link).toHaveAttribute("href", `/tours/${tour.id}`);
    }
}

/** A server with only the tours Galaxy ships. */
export const CoreTours: Story = {
    play: async (context) => {
        await context.step("Read a link to each shipped tour", async () => {
            await seeTours(context, CORE_TOURS);
        });
    },
    parameters: { msw: { handlers: { tours: tourList(CORE_TOURS) } } },
};

/** A tour an admin added, whose description is formatted with HTML. */
export const FormattedDescription: Story = {
    play: async ({ canvas, step }) => {
        await step("Read the tour's formatted description", async () => {
            const link = await canvas.findByRole("link", { name: /RNA-seq Read Mapping/ }, { timeout: 5000 });
            const toolName = within(link).getByText("HISAT2", { exact: true });
            await expect(toolName).toBeVisible();
            await expect(toolName.tagName).toBe("B");
            await expect(link).toHaveTextContent(
                "Map paired-end reads with HISAT2 and count reads per gene with featureCounts.",
            );
        });
    },
    parameters: { msw: { handlers: { tours: tourList([RNA_SEQ_TOUR]) } } },
};

/** Search by a tour's name or description, then clear the search to restore the list. */
export const SearchesTours: Story = {
    parameters: CoreTours.parameters,
    play: async (context) => {
        const { canvas, userEvent, step } = context;
        await step("Start with all shipped tours", async () => {
            await seeTours(context, CORE_TOURS);
        });
        await step("Find the history tour by name, regardless of capitalization", async () => {
            await userEvent.type(canvas.getByRole("textbox"), "HISTORY");
            await seeTours(
                context,
                CORE_TOURS.filter((tour) => tour.id === "core.history"),
            );
        });
        await step("Find a tour by its description", async () => {
            const search = canvas.getByRole("textbox");
            await userEvent.clear(search);
            await userEvent.type(search, "multiple datasets");
            await seeTours(
                context,
                CORE_TOURS.filter((tour) => tour.id === "core.windows"),
            );
        });
        await step("Clear the search and read all tours again", async () => {
            await userEvent.click(canvas.getByRole("button", { name: /Clear Search/ }));
            await expect(canvas.getByRole("textbox")).toHaveValue("");
            await seeTours(context, CORE_TOURS);
        });
    },
};
