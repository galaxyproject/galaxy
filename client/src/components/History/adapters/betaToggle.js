const USE_BETA_HISTORY_STORAGE_KEY = "useBetaHistory";

export const shouldUseBetaHistory = (instanceDefault) => {
    // If there's a value set, respect it.  Otherwise get instance default from config.
    const userPrefBetaHistory = sessionStorage.getItem(USE_BETA_HISTORY_STORAGE_KEY);
    if (userPrefBetaHistory != null) {
        return userPrefBetaHistory === "1";
    } else {
        return instanceDefault;
    }
};

export const switchToLegacyHistoryPanel = () => {
    sessionStorage.setItem(USE_BETA_HISTORY_STORAGE_KEY, 0);
    location.reload();
};

export const switchToBetaHistoryPanel = () => {
    sessionStorage.setItem(USE_BETA_HISTORY_STORAGE_KEY, 1);
    location.reload(false);
};
