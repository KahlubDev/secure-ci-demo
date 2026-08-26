use axum::{routing::get, Router};

pub fn create_app() -> Router {
    Router::new()
        .route("/", get(home))
        .route("/health", get(health))
}

async fn home() -> &'static str {
    "Secure CI Demo API"
}

async fn health() -> &'static str {
    "OK"
}