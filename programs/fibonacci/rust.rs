fn fib(a: i32) -> i32 {
    if a < 2 {
        a
    } else {
        fib(a - 1) + fib(a - 2)
    }
}


fn main() {
    println!("{}", fib(30));
}
