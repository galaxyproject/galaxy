/** Information to access the IndexedDB database. */
export interface IndexedDBInfo {
    /**
     * The name of the database.
     *
     * This should be unique to avoid conflicts with other databases.
     * It is recommended to use a descriptive name that reflects the purpose of the database.
     */
    name: string;

    /**
     * The name of the object store.
     *
     * This is the name of the collection of records within the database.
     */
    store: string;

    /**
     * The version of the database.
     *
     * This is used to manage changes to the database schema.
     * When the version number is incremented, the onupgradeneeded event is triggered,
     * allowing you to modify the database structure.
     * It is important to keep track of the version number to ensure compatibility with existing data.
     */
    version: number;
}

/** Represents a file stored in IndexedDB. */
export interface IndexedDBFile {
    /**
     * The name or path of the file.
     * This is the key used to store and retrieve the file in IndexedDB.
     * It should be unique within the object store.
     */
    name: string;

    /** The file data stored in the database as a Blob. */
    fileData: Blob;
}

export function useIndexedDBFileStorage(dbAccess: IndexedDBInfo) {
    async function openDB(): Promise<IDBDatabase> {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(dbAccess.name, dbAccess.version);
            request.onsuccess = () => resolve(request.result);
            request.onerror = (e) => reject(e);
        });
    }

    async function storeFile(name: string, fileData: Blob) {
        const db = await openDB();
        const tx = db.transaction(dbAccess.store, "readwrite");
        const store = tx.objectStore(dbAccess.store);
        store.put({ name, fileData });
        db.close();
    }

    async function getAllStoredFiles(): Promise<IndexedDBFile[]> {
        const db = await openDB();
        const tx = db.transaction(dbAccess.store, "readonly");
        const store = tx.objectStore(dbAccess.store);
        const request = store.getAll();
        return new Promise((resolve) => {
            request.onsuccess = () => {
                resolve(request.result);
            };
        });
    }

    async function clearDatabaseStore() {
        const db = await openDB();
        const tx = db.transaction(dbAccess.store, "readwrite");
        const store = tx.objectStore(dbAccess.store);
        store.clear();
    }

    return {
        storeFile,
        getAllStoredFiles,
        clearDatabaseStore,
    };
}
