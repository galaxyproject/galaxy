export function extractEmbeddedJs(inputString: string, fieldRegex?: RegExp): { fragment: string; start: number }[] {
    let i = 0;
    let end = inputString.length;
    if (fieldRegex) {
        const fieldMatch = fieldRegex.exec(inputString);
        if (fieldMatch && fieldMatch.length) {
            i = fieldMatch.index;
            end = i + fieldMatch[0].length;
        }
    }
    const matches: { fragment: string; start: number }[] = [];

    while (i < end) {
        if (inputString[i] === "$" && inputString[i + 1] === "(") {
            let depth = 0;
            const startIndex = i + 2;
            i += 2; // Skip past "$("

            while (i < end) {
                if (inputString[i] === "(") {
                    depth++;
                } else if (inputString[i] === ")") {
                    if (depth === 0) {
                        // Match ends
                        matches.push({
                            fragment: inputString.substring(startIndex, i + 1),
                            start: startIndex,
                        });
                        break;
                    }
                    depth--;
                }
                i++;
            }
        } else {
            i++;
        }
    }

    return matches;
}
