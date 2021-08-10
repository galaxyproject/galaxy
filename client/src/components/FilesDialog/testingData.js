export const rootResponse = [
    {
        id: "_ftp",
        type: "gxftp",
        uri_root: "gxftp://",
        label: "FTP Directory",
        doc: "Galaxy User's FTP Directory",
        writable: true,
        requires_roles: null,
        requires_groups: null,
    },
    {
        id: "pdb-gzip",
        type: "posix",
        uri_root: "gxfiles://pdb-gzip",
        label: "PDB",
        doc: "Protein Data Bank (PDB)",
        writable: true,
        requires_roles: null,
        requires_groups: null,
    },
];
