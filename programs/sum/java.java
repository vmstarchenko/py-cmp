class java {
    public static void main(String[] argv) {
        int s = 0;
        int last = Integer.parseInt(argv[0]);
        for (int i = 0; i < last; ++i) {
            s += i;
            if (s > 1000000000) {
                s = 0;
            }
        }
        System.out.println(s);
    }
}
