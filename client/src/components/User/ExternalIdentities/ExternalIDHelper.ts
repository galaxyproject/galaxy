import axios from "axios";

import { withPrefix } from "@/utils/redirect";
import { rethrowSimple } from "@/utils/simple-error";

/** Shape of the OIDC config object coming from Galaxy’s `/api/config`. */
export type OIDCConfig = Record<
    string,
    {
        icon?: string;
        label?: string;
        custom_button_text?: string;
        end_user_registration_endpoint?: string;
    }
>;

/** Return the per-IDP config, minus anything the caller wants to hide. */
export function getFilteredOIDCIdps(oidcConfig: OIDCConfig, exclude: string[] = []): OIDCConfig {
    const blacklist = new Set(["cilogon", "custos", ...exclude]);
    const filtered: OIDCConfig = {};
    Object.entries(oidcConfig).forEach(([idp, cfg]) => {
        if (!blacklist.has(idp)) {
            filtered[idp] = cfg;
        }
    });
    return filtered;
}

/** Do we need to show the institution picker at all? */
export const getNeedShowCilogonInstitutionList = (cfg: OIDCConfig): boolean => {
    return Boolean(cfg.cilogon || cfg.custos);
};

/**
 * Generic OIDC login (all providers *except* CILogon/Custos).
 * Returns the redirect URI Galaxy gives back, or throws.
 */
export async function submitOIDCLogon(idp: string, redirectParam: string | null = null): Promise<string | null> {
    const formData = new FormData();
    formData.append("next", redirectParam ?? "");

    try {
        const { data } = await axios.post<{ redirect_uri?: string }>(withPrefix(`/authnz/${idp}/login`), formData, {
            withCredentials: true,
        });
        return data.redirect_uri ?? null;
    } catch (error) {
        rethrowSimple(error);
    }
}

/**
 * CILogon/Custos login.
 * @param idp        "cilogon" | "custos"
 * @param useIDPHint If true, append ?idphint=
 * @param idpHint    The entityID to hint with (ignored when useIDPHint = false)
 */
export async function submitCILogon(idp: string, useIDPHint = false, idpHint?: string): Promise<string | null> {
    let url = withPrefix(`/authnz/${idp}/login/`);
    if (useIDPHint && idpHint) {
        url += `?idphint=${encodeURIComponent(idpHint)}`;
    }

    try {
        const { data } = await axios.post<{ redirect_uri?: string }>(url);
        return data.redirect_uri ?? null;
    } catch (error) {
        rethrowSimple(error);
    }
}

export function isOnlyOneOIDCProviderConfigured(config: OIDCConfig): boolean {
    return Object.keys(config).length === 1;
}

export async function redirectToSingleProvider(config: OIDCConfig): Promise<string | null> {
    const providers = Object.keys(config);

    if (providers.length !== 1) {
        return null;
    }

    const idp = providers[0];
    if (!idp) {
        throw new Error("OIDC provider key is undefined.");
    }

    if (idp === "cilogon" || idp === "custos") {
        const redirectUri = await submitCILogon(idp, false);
        return redirectUri;
    } else {
        const redirectUri = await submitOIDCLogon(idp, "");
        return redirectUri;
    }
}
