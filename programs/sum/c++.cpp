#include <iostream>
#include <stdlib.h>

int main(int argc, char* argv[]) {
    int last = atoi(argv[1]);
    int sum = 0;
    for (int i = 0; i < last; ++i) {
        sum += i;
        if (sum > 1000000000) {
            sum = 0;
        }
    }

    std::cout << sum << std::endl;
    return 0;
}
