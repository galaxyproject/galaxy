export function _setUserLocale(user, config) {
    sessionStorage.setItem("currentLocale", "en");
}

export function _getUserLocale(user, config) {
    return "en";
}

export default function localize(l) {
    return l;
}
