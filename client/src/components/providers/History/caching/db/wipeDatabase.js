import { dbs } from "./pouch";

/**
 * Erases all stored database instances
 */
export async function wipeDatabase() {
    for (const db of dbs.values()) {
        await db.erase();
    }
}
