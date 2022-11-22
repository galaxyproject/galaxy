import { useMarkdown } from "composables/markdown";

describe("useMarkdown", () => {
    describe("renderMarkdown", () => {
        it("should render HTML from Markdown string", () => {
            const { renderMarkdown } = useMarkdown();
            const html = renderMarkdown("# Title");

            expect(html).toContain("<h1>");
        });

        it("should open links in the same page by default", () => {
            const { renderMarkdown } = useMarkdown();
            const html = renderMarkdown("[my link](https://galaxyproject.org)");
            expect(html).not.toContain("_blank");
        });

        it("should open links in a new page when openLinksInNewPage is true", () => {
            const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });
            const html = renderMarkdown("[my link](https://galaxyproject.org)");
            expect(html).toContain('target="_blank"');
        });
    });
});
