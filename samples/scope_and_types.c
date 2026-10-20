// Scope & Semantic Defects
// Demonstrates duplicate declarations in the same scope, scope leakage, and void type misuse.
int compute_scope(int val) {
    int counter = 10;
    // Duplicate declaration in same scope
    int counter = 20;

    if (val > 0) {
        int inner_scoped_var = 50;
    }

    // Scope violation: inner_scoped_var is not accessible in outer scope
    int total = inner_scoped_var + counter;

    return total;
}
