describe("Sample Test", () => {
    it("hey look, tests run", () => {
        assert.equal(1, 1);
    });

    it("prove I can use a Proxy", () => {
        let target = {};
        let thing = new Proxy(target, {});
        thing.foo = 232;
        assert.equal(target.foo, thing.foo);
    });
});
