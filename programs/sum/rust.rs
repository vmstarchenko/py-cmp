fn main() {
    let last = std::env::args().nth(1).unwrap().parse::<i32>().unwrap();
    let mut sum = 0;
    for i in 0..last {
        sum += i;
        if sum > 1000000000 {
            sum = 0;
        }
    }
    println!("{}", sum);
}
