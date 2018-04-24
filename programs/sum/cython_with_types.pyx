import sys

def main():
    cdef int s = 0
    for i in range(int(sys.argv[1])):
        s += i
        if s > 1000000000:
            s = 0
    print(s)

if __name__ == "__main__":
    main()
