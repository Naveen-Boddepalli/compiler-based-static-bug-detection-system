// Clean, Well-Formed Program (0 Errors, 0 Warnings)
// Demonstrates correct static analysis passing across functions, loops, and flow.
int factorial(int n) {
    int result = 1;
    int i = 1;
    while (i <= n) {
        result = result * i;
        i++;
    }
    return result;
}

int main() {
    int input = 5;
    int output = factorial(input);
    return output;
}
