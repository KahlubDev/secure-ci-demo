pub mod database;
pub mod handlers;
pub mod models;
pub mod routes;
pub mod state;

use axum::Router;

use state::AppState;

pub async fn build_app() -> Router {
    let db = database::connect_db().await;

    let state = AppState { db };

    routes::create_routes(state)
}

pub fn test_app() -> Router {
    Router::new()
        .route("/", axum::routing::get(home))
        .route("/health", axum::routing::get(health))
}

pub async fn home() -> &'static str {
    "Secure CI Demo API"
}

pub async fn health() -> &'static str {
    "OK"
}