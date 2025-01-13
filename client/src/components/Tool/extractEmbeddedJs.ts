export function extractEmbeddedJs(inputString: string): { fragment: string; start: number }[] {
    const matches: { fragment: string; start: number }[] = [];
    let i = 0;

    while (i < inputString.length) {
        if (inputString[i] === "$" && inputString[i + 1] === "(") {
            let depth = 0;
            const startIndex = i;
            i += 2; // Skip past "$("

            while (i < inputString.length) {
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
