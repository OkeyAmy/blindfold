// blindfold multi-language fixture (Rust)
fn add(a: i32, b: i32) -> i32 { a + b }

#[test]
fn justified() {
    assert_eq!(add(2, 3), 5); // blindfold: math — 2+3 is 5
}

#[test]
fn unjustified() {
    assert_eq!(add(10, 20), 30);
}
