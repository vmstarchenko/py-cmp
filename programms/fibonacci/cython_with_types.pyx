def fib(int a):
    if a < 2:
        return a
    return fib(a - 1) + fib(a - 2)

def main():
    print(fib(30))

if __name__ == "__main__":
    main()
