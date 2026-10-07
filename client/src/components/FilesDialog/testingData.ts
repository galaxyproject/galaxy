import type { BrowsableFilesSourcePlugin } from "@/api/remoteFiles";

export const ftpId = "_ftp";
export const rootId = "pdb-gzip";
export const directoryId = "gxfiles://pdb-gzip/directory1";
export const subDirectoryId = "gxfiles://pdb-gzip/directory1/subdirectory1";
export const subSubDirectoryId = "gxfiles://pdb-gzip/directory1/subdirectory1/subsubdirectory";

// TODO these types should be generated from the schema
interface RemoteEntry {
    class: string;
    name: string;
    uri: string;
    path: string;
}

export interface RemoteDirectory extends RemoteEntry {
    class: "Directory";
}

export interface RemoteFile extends RemoteEntry {
    class: "File";
    size: number;
    ctime: string;
}

export type RemoteFilesList = (RemoteDirectory | RemoteFile)[];

export const rootResponse: BrowsableFilesSourcePlugin[] = [
    {
        id: "_ftp",
        type: "gxftp",
        uri_root: "gxftp://",
        label: "FTP Directory",
        doc: "Galaxy User's FTP Directory",
        writable: true,
        browsable: true,
        supports: {
            pagination: false,
            search: false,
            sorting: false,
        },
    },
    {
        id: "pdb-gzip",
        type: "posix",
        uri_root: "gxfiles://pdb-gzip",
        label: "PDB",
        doc: "Protein Data Bank (PDB)",
        writable: true,
        browsable: true,
        supports: {
            pagination: false,
            search: false,
            sorting: false,
        },
    },
    {
        id: "empty-dir",
        type: "posix",
        uri_root: "gxfiles://empty-dir",
        label: "Empty Directory",
        doc: "Empty Directory",
        writable: true,
        browsable: true,
        supports: {
            pagination: false,
            search: false,
            sorting: false,
        },
    },
    {
        id: "c5504eb8-51cf-4b44-88f8-24347c031f52",
        type: "ftp",
        label: "My own FTP",
        doc: "This FTP is accessible only by me",
        browsable: true,
        writable: true,
        supports: {
            pagination: true,
            search: true,
            sorting: false,
        },
        uri_root: "gxuserfiles://c5504eb8-51cf-4b44-88f8-24347c031f52",
    },
];

export const pdbResponse: RemoteFilesList = [
    {
        class: "File",
        name: "file2",
        size: 0,
        ctime: "2021-08-10T20:00:00Z",
        uri: "gxfiles://pdb-gzip/file2",
        path: "/file2",
    },
    {
        class: "File",
        name: "file1",
        size: 0,
        ctime: "2021-08-10T19:59:58Z",
        uri: "gxfiles://pdb-gzip/file1",
        path: "/file1",
    },
    { class: "Directory", name: "directory2", uri: "gxfiles://pdb-gzip/directory2", path: "/directory2" },
    { class: "Directory", name: "directory1", uri: "gxfiles://pdb-gzip/directory1", path: "/directory1" },
];

export const directory1RecursiveResponse: RemoteFilesList = [
    {
        class: "Directory",
        name: "subdirectory1",
        uri: "gxfiles://pdb-gzip/directory1/subdirectory1",
        path: "directory1/subdirectory1",
    },
    {
        class: "Directory",
        name: "subdirectory2",
        uri: "gxfiles://pdb-gzip/directory1/subdirectory2",
        path: "directory1/subdirectory2",
    },
    {
        class: "File",
        name: "directory1file2",
        size: 0,
        ctime: "2021-08-10T19:37:44Z",
        uri: "gxfiles://pdb-gzip/directory1/directory1file2",
        path: "directory1/directory1file2",
    },
    {
        class: "File",
        name: "directory1file1",
        size: 0,
        ctime: "2021-08-10T19:37:41Z",
        uri: "gxfiles://pdb-gzip/directory1/directory1file1",
        path: "directory1/directory1file1",
    },
    {
        class: "File",
        name: "directory1file3",
        size: 0,
        ctime: "2021-08-10T19:37:48Z",
        uri: "gxfiles://pdb-gzip/directory1/directory1file3",
        path: "directory1/directory1file3",
    },
    {
        class: "Directory",
        name: "subsubdirectory",
        uri: "gxfiles://pdb-gzip/directory1/subdirectory1/subsubdirectory",
        path: "directory1/subdirectory1/subsubdirectory",
    },
    {
        class: "File",
        name: "subsubfile",
        size: 0,
        ctime: "2021-07-29T21:52:38Z",
        uri: "gxfiles://pdb-gzip/directory1/subdirectory1/subsubdirectory/subsubfile",
        path: "directory1/subdirectory1/subsubdirectory/subsubfile",
    },
    {
        class: "File",
        name: "subdirectory2file",
        size: 0,
        ctime: "2021-08-10T19:38:39Z",
        uri: "gxfiles://pdb-gzip/directory1/subdirectory2/subdirectory2file",
        path: "directory1/subdirectory2/subdirectory2file",
    },
];

export const directory2RecursiveResponse: RemoteFilesList = [
    {
        class: "File",
        name: "directory2file1",
        size: 0,
        ctime: "2021-08-10T19:57:11Z",
        uri: "gxfiles://pdb-gzip/directory2/directory2file1",
        path: "directory2/directory2file1",
    },
    {
        class: "File",
        name: "directory2file2",
        size: 0,
        ctime: "2021-08-10T19:57:12Z",
        uri: "gxfiles://pdb-gzip/directory2/directory2file2",
        path: "directory2/directory2file2",
    },
];
export const directory1Response: RemoteFilesList = [
    {
        class: "File",
        name: "directory1file2",
        size: 0,
        ctime: "2021-08-10T19:37:44Z",
        uri: "gxfiles://pdb-gzip/directory1/directory1file2",
        path: "directory1/directory1file2",
    },
    {
        class: "Directory",
        name: "subdirectory1",
        uri: "gxfiles://pdb-gzip/directory1/subdirectory1",
        path: "directory1/subdirectory1",
    },
    {
        class: "Directory",
        name: "subdirectory2",
        uri: "gxfiles://pdb-gzip/directory1/subdirectory2",
        path: "directory1/subdirectory2",
    },
    {
        class: "File",
        name: "directory1file1",
        size: 0,
        ctime: "2021-08-10T19:37:41Z",
        uri: "gxfiles://pdb-gzip/directory1/directory1file1",
        path: "directory1/directory1file1",
    },
    {
        class: "File",
        name: "directory1file3",
        size: 0,
        ctime: "2021-08-10T19:37:48Z",
        uri: "gxfiles://pdb-gzip/directory1/directory1file3",
        path: "directory1/directory1file3",
    },
];
export const subsubdirectoryResponse: RemoteFilesList = [
    {
        class: "Directory",
        name: "subsubdirectory",
        uri: "gxfiles://pdb-gzip/directory1/subdirectory1/subsubdirectory",
        path: "directory1/subdirectory1/subsubdirectory",
    },
];

export const someErrorText = "some error text";
