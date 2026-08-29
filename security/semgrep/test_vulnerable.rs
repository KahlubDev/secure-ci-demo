fn main() {
    let title = "test";
    let query = format!(
        "SELECT * FROM notes WHERE title = '{}'",
        title
    );
    println!("{}", query);
}
