use axum::{
    extract::State,
    http::StatusCode,
    Json,
};
use sqlx::Row;
use validator::Validate;

use crate::{
    models::{CreateNoteRequest, Note},
    state::AppState,
};

pub async fn create_note(
    State(state): State<AppState>,
    Json(payload): Json<CreateNoteRequest>,
) -> Result<(StatusCode, Json<Note>), StatusCode> {
    if payload.validate().is_err() {
        return Err(StatusCode::BAD_REQUEST);
    }

    let id = payload.id();

    let result = sqlx::query(
        "INSERT INTO notes (id, title, content) VALUES (?, ?, ?)"
    )
    .bind(&id)
    .bind(&payload.title)
    .bind(&payload.content)
    .execute(&state.db)
    .await;

    if result.is_err() {
        return Err(StatusCode::INTERNAL_SERVER_ERROR);
    }

    let note = sqlx::query(
        "SELECT id, title, content, created_at FROM notes WHERE id = ?"
    )
    .bind(&id)
    .fetch_one(&state.db)
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    let note = Note {
        id: note.try_get("id").map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?,
        title: note.try_get("title").map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?,
        content: note.try_get("content").map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?,
        created_at: note.try_get("created_at").map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?,
    };

    Ok((StatusCode::CREATED, Json(note)))
}

pub async fn list_notes(
    State(state): State<AppState>,
) -> Result<Json<Vec<Note>>, StatusCode> {
    let rows = sqlx::query(
        "SELECT id, title, content, created_at FROM notes ORDER BY created_at DESC"
    )
    .fetch_all(&state.db)
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    let notes = rows
        .into_iter()
        .map(|row| {
            Ok(Note {
                id: row.try_get("id").map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?,
                title: row.try_get("title").map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?,
                content: row.try_get("content").map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?,
                created_at: row.try_get("created_at").map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?,
            })
        })
        .collect::<Result<Vec<_>, StatusCode>>()?;

    Ok(Json(notes))
}