import { publish, buffer, debounceTime } from "rxjs/operators";

export const burst = (period = 100) => {
    return publish((src) => {
        const flush = src.pipe(debounceTime(period));
        return src.pipe(buffer(flush));
    });
};
