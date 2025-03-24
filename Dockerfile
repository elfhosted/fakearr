# Use Go as the build stage
FROM golang:1.20-alpine AS builder
WORKDIR /app

# Copy Go modules and download dependencies
COPY go.mod ./
RUN go mod tidy && \
    go mod download

# Copy the rest of the application
COPY . .

# Build the binary
RUN go build -o fakearr

# Use a smaller final image
FROM alpine:latest
WORKDIR /root/
COPY --from=builder /app/fakearr .
CMD ["./fakearr"]
