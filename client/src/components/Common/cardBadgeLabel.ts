import localize from "@/utils/localization";

/**
 * Accessible name for a badge that acts on a user-supplied name, e.g. "Filter by owner jdoe".
 *
 * `localize()` is a whole-string lookup, so the action has to be translated on its own,
 * before the name (a username, a collection) is appended.
 */
export function badgeActionLabel(action: string, subject: string): string {
    return `${localize(action)} ${subject}`;
}
