/**
 * Escapes all RegExp control characters from a string, so it can be matched literally
 * @param string input string
 * @returns string with all control characters escaped
 *
 * @see https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Regular_Expressions
 */
export function escapeRegExp(string: string) {
    return string.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, "\\$&");
}
