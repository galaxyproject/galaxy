export const isBetaHistoryOpen = () => {
    return sessionStorage.getItem("useBetaHistory");
};

export const switchToLegacyHistoryPanel = () => {
    sessionStorage.removeItem("useBetaHistory");
    location.reload();
};

export const switchToBetaHistoryPanel = () => {
    sessionStorage.setItem("useBetaHistory", 1);
    location.reload(false);
};
