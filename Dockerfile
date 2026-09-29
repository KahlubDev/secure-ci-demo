# Multi-stage build: compile in a full Rust image, ship only the compiled
# binary in a minimal runtime image. The build toolchain never reaches
# the final image, so there's nothing extra in it for an attacker to abuse.

FROM rust:1.90-slim AS builder
WORKDIR /app
COPY Cargo.toml Cargo.lock ./
COPY src ./src
COPY migrations ./migrations
RUN cargo build --release

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /app/target/release/secure-ci-demo /app/secure-ci-demo
COPY --from=builder /app/migrations /app/migrations
EXPOSE 3000
CMD ["/app/secure-ci-demo"]
