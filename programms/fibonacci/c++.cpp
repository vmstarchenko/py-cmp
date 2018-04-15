#include <iostream>

int fib(int a) {
    if (a < 2)
        return a;
    return fib(a - 1) + fib(a - 2);
}


int main() {
    fib(30);
    return 0;
}
