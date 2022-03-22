// abstraction for copying text to the clipboard (or prompting if that isn't available)
import { Toast } from "ui/toast";

export function copy(text, notificationText) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            if (notificationText) {
                Toast.info(notificationText);
            }
        });
    } else {
        prompt("Copy to clipboard: Ctrl+C, Enter", text);
    }
}
