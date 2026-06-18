// blindfold multi-language fixture (Go)
package example

import "testing"

func add(a, b int) int { return a + b }

func TestJustified(t *testing.T) {
	if got := add(2, 3); got != 5 { // blindfold: math — 2+3 is 5
		t.Fatalf("got %d", got)
	}
}

func TestUnjustified(t *testing.T) {
	if got := add(10, 20); got != 30 {
		t.Fatalf("got %d", got)
	}
}
