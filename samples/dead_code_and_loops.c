// Dead Code & Control-Flow Defects
// Demonstrates statements after unconditional return, dead loop conditions, and unused variables.
int process_values(int limit) {
    int unused_cache = 100;

    // Dead loop: condition is constant false (0)
    while (0) {
        int dead_iteration = 1;
    }

    if (limit > 50) {
        return 1;
        // Unreachable statement after unconditional return
        int unreachable_after_return = limit * 2;
    }

    return 0;
}
