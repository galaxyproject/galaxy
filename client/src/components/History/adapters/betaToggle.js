const betaKey = "useBetaHistory";

export const isBetaHistoryOpen = () => {
    return sessionStorage.getItem(betaKey);
};

export const switchToLegacyHistoryPanel = () => {
    sessionStorage.removeItem(betaKey);
    location.reload();
};

export const switchToBetaHistoryPanel = () => {
    sessionStorage.setItem(betaKey, 1);
    location.reload();
};
