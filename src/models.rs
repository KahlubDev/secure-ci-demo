use serde::{Deserialize, Serialize};
use uuid::Uuid;
use validator::Validate;

#[derive(Debug, Serialize)]
pub struct Note {
    pub id: String,
    pub title: String,
    pub content: String,
    pub created_at: Option<String>,
}

#[derive(Debug, Deserialize, Validate)]
pub struct CreateNoteRequest {
    #[validate(length(min = 1, max = 100))]
    pub title: String,

    #[validate(length(min = 1, max = 5000))]
    pub content: String,
}

impl CreateNoteRequest {
    pub fn id(&self) -> String {
        Uuid::new_v4().to_string()
    }
}