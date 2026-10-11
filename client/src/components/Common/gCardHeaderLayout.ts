/**
 * Where a GCard header places its badges:
 * - "inline": one row of checkbox, title, badges and actions.
 * - "column": the title on the left, the badges directly under the actions in a right-hand column.
 * - "stacked": the badges on their own full-width row below the title and actions.
 */
export type GCardHeaderLayout = "inline" | "column" | "stacked";

export interface GCardHeaderWidths {
    /** Width of the header's content box */
    available: number;
    /** Gap between the header's items */
    gap: number;
    /** Narrowest the title may get */
    titleMin: number;
    /** Width of the actions group, undefined when the card has none */
    actions?: number;
    /** Width of the badges and indicators, undefined when the card has none */
    badges?: number;
    /** Width of the select checkbox, undefined when the card has none */
    select?: number;
}

/**
 * Picks the first layout that keeps the title at least `titleMin` wide. The widths must not depend on the
 * layout that is currently applied, so applying the result cannot change it.
 */
export function chooseHeaderLayout(widths: GCardHeaderWidths): GCardHeaderLayout {
    const { actions, available, badges, gap, select, titleMin } = widths;
    if (badges === undefined) {
        return "inline";
    }
    const selectWidth = select === undefined ? 0 : select + gap;
    const actionsWidth = actions === undefined ? 0 : actions + gap;
    if (selectWidth + titleMin + gap + badges + actionsWidth <= available) {
        return "inline";
    }
    if (actions !== undefined && selectWidth + titleMin + gap + Math.max(badges, actions) <= available) {
        return "column";
    }
    return "stacked";
}
