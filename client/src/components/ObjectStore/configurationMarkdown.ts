import MarkdownIt from "markdown-it";

export function markup(markup: string, adminConfigured: boolean): string | null {
    let markupHtml;
    const allowHtml = adminConfigured ? true : false;
    if (markup) {
        markupHtml = MarkdownIt({ html: allowHtml }).render(markup);
    } else {
        markupHtml = null;
    }
    return markupHtml;
}
