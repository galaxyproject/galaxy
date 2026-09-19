export interface Citation {
    raw: string;
    cite: {
        data: {
            URL: string;
        }[];
        format: (
            format: string,
            options: {
                format: string;
                template: string;
                lang: string;
            },
        ) => string;
    };
}

export interface CitationsResult {
    citations: Citation[];
    warnings: string[];
}
