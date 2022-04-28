const USE_LEGACY_HISTORY_STORAGE_KEY = "useLegacyHistory";

export const shouldUseLegacyHistory = (instanceDefaultUseLegacyHistory) => {
    // If there's a value set, respect it.  Otherwise get instance default from config.
    const userPrefLegacyHistory = sessionStorage.getItem(USE_LEGACY_HISTORY_STORAGE_KEY);
    if (userPrefLegacyHistory != null) {
        return userPrefLegacyHistory === "1";
    } else {
        return instanceDefaultUseLegacyHistory;
    }
};

export const switchToLegacyHistoryPanel = () => {
    sessionStorage.setItem(USE_LEGACY_HISTORY_STORAGE_KEY, 1);
    location.reload();
};

export const switchToBetaHistoryPanel = () => {
    sessionStorage.setItem(USE_LEGACY_HISTORY_STORAGE_KEY, 0);
    location.reload();
};
