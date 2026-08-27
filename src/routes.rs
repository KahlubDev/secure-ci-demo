use axum::{
    routing::{get, post},
    Router,
};

use crate::{
    handlers::{create_note, list_notes},
    state::AppState,
};

pub fn create_routes(state: AppState) -> Router {
    Router::new()
        .route("/", get(super::home))
        .route("/health", get(super::health))
        .route("/notes", post(create_note).get(list_notes))
        .with_state(state)
}