import MarkdownIt from "markdown-it";

export function adminMarkup(markup: string): string | null {
    let markupHtml;
    if (markup) {
        markupHtml = MarkdownIt({ html: true }).render(markup);
    } else {
        markupHtml = null;
    }
    return markupHtml;
}
