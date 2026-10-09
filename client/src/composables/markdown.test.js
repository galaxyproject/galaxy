import { describe, expect, it } from "vitest";

import { useMarkdown } from "./markdown";

describe("useMarkdown", () => {
    describe("renderMarkdown", () => {
        it("renders a Markdown heading with its text", () => {
            const { renderMarkdown } = useMarkdown();
            const html = renderMarkdown("# Title");

            expect(html).toContain("<h1>Title</h1>");
        });

        it("renders links that open in the same page by default", () => {
            const { renderMarkdown } = useMarkdown();
            const html = renderMarkdown("[my link](https://galaxyproject.org)");

            expect(html).toContain('<a href="https://galaxyproject.org">my link</a>');
            expect(html).not.toContain("_blank");
        });

        it("renders links that open in a new page when requested", () => {
            const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });
            const html = renderMarkdown("[my link](https://galaxyproject.org)");

            expect(html).toContain('<a href="https://galaxyproject.org" target="_blank">my link</a>');
            expect(html).toContain('target="_blank"');
        });
    });
});
