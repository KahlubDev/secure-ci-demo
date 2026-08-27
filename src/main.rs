use secure_ci_demo::build_app;

#[tokio::main]
async fn main() {
    let app = build_app().await;

    let listener = tokio::net::TcpListener::bind("127.0.0.1:3000")
        .await
        .unwrap();

    println!("Server running at http://127.0.0.1:3000");

    axum::serve(listener, app)
        .await
        .unwrap();
}