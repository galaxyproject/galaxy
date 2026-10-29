export type PageWindowItem = { kind: "page"; key: string; page: number } | { kind: "ellipsis"; key: string };

export interface PageWindowOptions {
    /** Number of pages, at least 1 */
    total: number;
    /** Current page, within 1..total */
    current: number;
    /** Page numbers in the window, not counting pinned first/last numbers; at least 1 */
    limit: number;
    firstNumber: boolean;
    lastNumber: boolean;
    hideEllipsis: boolean;
}

// At this limit or below the window is a plain run of pages, with no ellipses
const ELLIPSIS_THRESHOLD = 3;

function pages(from: number, to: number): PageWindowItem[] {
    return Array.from({ length: to - from + 1 }, (_, index) => ({
        kind: "page",
        key: `page-${from + index}`,
        page: from + index,
    }));
}

/** The page numbers and ellipses a pager shows, in order. */
export function pageWindow(options: PageWindowOptions): PageWindowItem[] {
    const { total, current, limit, firstNumber, lastNumber, hideEllipsis } = options;
    const firstPage = (show: boolean) => (show ? pages(1, 1) : []);
    const lastPage = (show: boolean) => (show ? pages(total, total) : []);
    const gap = (side: "start" | "end"): PageWindowItem[] =>
        hideEllipsis ? [] : [{ kind: "ellipsis", key: `ellipsis-${side}` }];
    const leadSlots = firstNumber ? 1 : 0;
    const tailSlots = lastNumber ? 1 : 0;

    if (limit <= ELLIPSIS_THRESHOLD) {
        if (total <= limit + leadSlots + tailSlots) {
            return pages(1, total);
        }
        // A pinned end inside the window frees its slot for one more page, keeping the item count
        let start = Math.min(Math.max(current - Math.floor(limit / 2), 1), total - limit + 1);
        let end = start + limit - 1;
        if (firstNumber && start === 1) {
            end += 1;
        } else if (lastNumber && end === total) {
            start -= 1;
        }
        return [...firstPage(firstNumber && start > 1), ...pages(start, end), ...lastPage(lastNumber && end < total)];
    }

    // Pages around the current one, plus one slot per ellipsis and pinned end: the item count stays
    // the same from page to page, so the buttons do not shift under the pointer.
    const middle = limit - 2;
    const slots = middle + 2 + leadSlots + tailSlots;
    if (total <= slots) {
        return pages(1, total);
    }

    const start = current - Math.floor((middle - 1) / 2);
    const end = start + middle - 1;
    if (start <= leadSlots + 2) {
        return [...pages(1, slots - 1 - tailSlots), ...gap("end"), ...lastPage(lastNumber)];
    }
    if (end >= total - tailSlots - 1) {
        return [...firstPage(firstNumber), ...gap("start"), ...pages(total - (slots - 2 - leadSlots), total)];
    }
    return [...firstPage(firstNumber), ...gap("start"), ...pages(start, end), ...gap("end"), ...lastPage(lastNumber)];
}
