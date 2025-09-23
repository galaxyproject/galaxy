/**
 * Custom options for the monkeypatched router.push() method
 * Used to control window manager behavior and force navigation
 */
export interface RouterPushOptions {
    // Title for window manager frame
    title?: string;
    // Force reload (currently by adding timestamp to URL)
    force?: boolean;
    // Explicit WM bypass -- prevent opening in window manager even if active
    preventWindowManager?: boolean;
}
