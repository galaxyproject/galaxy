import { escapeRegExp } from "@/utils/regExp";

/** Matches exactly `text`, since `toHaveTextContent` with a string matches a substring. */
export function exactly(text: string) {
    return new RegExp(`^${escapeRegExp(text)}$`);
}
