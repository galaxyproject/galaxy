declare module 'zxcvbn' {
    interface ZxcvbnFeedback {
        warning: string;
        suggestions: string[];
    }

    interface ZxcvbnResult {
        crack_times_display: any;
        score: number; // Password strength score (0-4)
        feedback: ZxcvbnFeedback; // Feedback about the password
        guesses: number; // Estimated number of guesses to crack the password
        guesses_log10: number; // Log10 of the guesses
        calc_time: number; // Time taken for the calculation (in milliseconds)
        sequence: any[]; // Sequence of patterns used to match the password
    }

    export default function zxcvbn(password: string): ZxcvbnResult;
}
