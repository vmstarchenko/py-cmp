import sys

def main():
    s = 0
    last = int(sys.argv[1])
    print(last)
    for i in range(last):
        s += i
        if s > 1000000000:
            s = 0
    print(s)

if __name__ == "__main__":
    main()
