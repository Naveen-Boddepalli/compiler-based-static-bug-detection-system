// Division by Zero & Safety Defects
// Demonstrates constant division/modulo by zero and constant propagation.
int calculate(int base) {
    int zero_val = 0;
    int direct_div = base / 0;
    int propagated_div = base / zero_val;
    int folded_div = base / (10 - 10);
    int zero_mod = base % 0;
    return direct_div + propagated_div + folded_div + zero_mod;
}
