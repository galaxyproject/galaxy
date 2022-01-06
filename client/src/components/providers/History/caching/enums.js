// seek types

const seeks = { ASC: "asc", DESC: "desc" };

seeks.isValid = (val) => {
    return Object.values(SEEK).some((v) => v == val);
};

export const SEEK = seeks;
