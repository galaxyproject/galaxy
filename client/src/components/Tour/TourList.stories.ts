import type { Meta, StoryObj } from "@storybook/vue3-vite";

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

/** A server with only the tours Galaxy ships. */
export const CoreTours: Story = {
    parameters: { msw: { handlers: { tours: tourList(CORE_TOURS) } } },
};

/** A tour an admin added, whose description is formatted with HTML. */
export const FormattedDescription: Story = {
    parameters: { msw: { handlers: { tours: tourList([RNA_SEQ_TOUR]) } } },
};
