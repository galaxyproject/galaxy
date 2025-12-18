/** Terms to identify summary sections in the help text */
const SUMMARY_HEADER_TERMS = ["what it does", "synopsis", "syntax", "purpose", "what this tool does"];

/** Given the help text, extracts and returns a summary by detecting relevant HTML elements
 * that could contain a short description of the tool.
 */
export function parseHelpForSummary(help: string): string {
    let summary = "";
    const parser = new DOMParser();
    const helpDoc = parser.parseFromString(help, "text/html");

    const xpaths: string[] = [];

    // Generate XPath expressions for each term
    SUMMARY_HEADER_TERMS.forEach((term) => {
        // Case-insensitive strong element check
        xpaths.push(
            `//strong[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ?', 'abcdefghijklmnopqrstuvwxyz'), '${term}')]/../following-sibling::*`,
        );

        // Case-sensitive h1 element check (capitalize first letter)
        const capitalizedTerm = term.charAt(0).toUpperCase() + term.slice(1);
        xpaths.push(`//h1[text()='${capitalizedTerm}']/following-sibling::*`);
    });

    const matches: Node[] = [];
    xpaths.forEach((xpath) => {
        const newNode = helpDoc.evaluate(
            xpath,
            helpDoc,
            null,
            XPathResult.FIRST_ORDERED_NODE_TYPE,
            null,
        ).singleNodeValue;
        if (newNode) {
            matches.push(newNode);
        }
    });

    matches.forEach((match) => {
        if (match) {
            summary += (match as HTMLElement).innerHTML + "\n";
        }
    });
    return summary;
}
