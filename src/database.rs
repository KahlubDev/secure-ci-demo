use sqlx::{sqlite::SqlitePoolOptions, SqlitePool};

pub async fn connect_db() -> SqlitePool {
    let pool = SqlitePoolOptions::new()
        .max_connections(5)
        .connect("sqlite:notes.db")
        .await
        .expect("Failed to connect database");

    sqlx::migrate!("./migrations")
        .run(&pool)
        .await
        .expect("Migration failed");

    pool
}