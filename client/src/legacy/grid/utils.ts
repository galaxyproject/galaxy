import { getGalaxyInstance } from "@/app";
import _l from "@/utils/localization";

export function setWindowTitle(title: string): void {
    const Galaxy = getGalaxyInstance();
    if (title) {
        window.document.title = `Galaxy ${Galaxy.config.brand ? ` | ${Galaxy.config.brand}` : ""} | ${_l(title)}`;
    } else {
        window.document.title = `Galaxy ${Galaxy.config.brand ? ` | ${Galaxy.config.brand}` : ""}`;
    }
}
