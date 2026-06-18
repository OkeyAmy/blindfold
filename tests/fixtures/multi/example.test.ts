// blindfold multi-language fixture (TypeScript)
function slug(s: string): string { return s.toLowerCase().replace(/ /g, "-"); }

it("justified", () => {
  expect(slug("A B")).toBe("a-b"); // blindfold: doc — slug lowercases, spaces -> dash
});

it("unjustified", () => {
  expect(slug("Hi There")).toBe("hi-there");
});

it("confessed", () => {
  expect(slug("X Y")).toBe("x-y"); // blindfold: snapshot — recorded from a run
});
