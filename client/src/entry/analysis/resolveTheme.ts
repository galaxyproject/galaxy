export type ThemeVars = Record<string, string>;
export type Themes = Record<string, ThemeVars>;

export interface ResolveThemeArgs {
    /** Whether the app is rendered chrome-free (embed iframe / in-frame). */
    embedded: boolean;
    /** All configured themes as flat CSS-variable dicts (``config.themes``). */
    themes: Themes | null | undefined;
    /** ``?theme=`` query value (vue-router gives string | string[] | undefined). */
    queryTheme?: string | string[] | null;
    /** The logged-in user's selected theme id (normal app only). */
    currentTheme?: string | null;
}

/**
 * Resolve which theme's CSS-variable dict to apply at the app root.
 *
 * Embedded pages (e.g. the Loom/Orbit notebook iframe) have no user theme pref and
 * no masthead picker, so the embedder selects a theme via ``?theme=<id>``. That is
 * honored *only* when embedded, so it never overrides a logged-in user's chosen
 * theme in the normal app. Unknown/absent ids yield ``null`` (no theme applied).
 *
 * In the normal app the user's ``currentTheme`` wins, falling back to the first
 * configured theme; no themes configured yields ``null``.
 */
export function resolveTheme({ embedded, themes, queryTheme, currentTheme }: ResolveThemeArgs): ThemeVars | null {
    const all = themes || {};

    if (embedded) {
        const requested = Array.isArray(queryTheme) ? queryTheme[0] : queryTheme;
        if (typeof requested === "string" && requested in all) {
            return all[requested];
        }
        return null;
    }

    const keys = Object.keys(all);
    if (keys.length === 0) {
        return null;
    }
    const selected = currentTheme && keys.includes(currentTheme) ? currentTheme : keys[0];
    return all[selected];
}
