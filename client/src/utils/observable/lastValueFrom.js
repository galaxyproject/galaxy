// Rxjs is deprecating .toPromise in favor of a function named lastValueFrom
// which is not yet availble.

export const lastValueFrom = (obs$) => {
    return new Promise((resolve, reject) => {
        obs$.subscribe({
            complete() {
                resolve();
            },
            error(err) {
                reject(err);
            },
        });
    });
};
