export function getHistories() {
    return JSON.parse(localStorage.getItem("selectedHistories")) || [];
}

export function addHistory(historyId) {
    const selectedHistories = getHistories();
    localStorage.setItem("selectedHistories", JSON.stringify([...selectedHistories, { id: historyId }]));
}

export function removeHistory(historyId) {
    const selectedHistories = getHistories();
    localStorage.setItem("selectedHistories", JSON.stringify(selectedHistories.filter((h) => h.id !== historyId)));
}
