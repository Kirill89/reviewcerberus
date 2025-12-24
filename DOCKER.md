# Docker Build and Publish Guide

## Building the Image

Build for your platform (using Makefile):

```bash
make docker-build
```

Or directly with Docker:

```bash
docker build -t kirill89/reviewcerberus-cli:latest .
```

Build for multiple platforms (recommended for publishing):

```bash
VERSION=0.1.0 make docker-build-push
```

Or directly with Docker:

```bash
docker buildx build --platform linux/amd64,linux/arm64 \
  -t kirill89/reviewcerberus-cli:latest \
  -t kirill89/reviewcerberus-cli:0.1.0 \
  --push .
```

## Testing Locally

Test with Anthropic API:

```bash
docker run --rm -it -v $(pwd):/repo \
  -e MODEL_PROVIDER=anthropic \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  kirill89/reviewcerberus-cli:latest \
  --repo-path /repo --output /repo/review.md
```

Test with AWS Bedrock:

```bash
docker run --rm -it -v $(pwd):/repo \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -e AWS_REGION_NAME=$AWS_REGION_NAME \
  kirill89/reviewcerberus-cli:latest \
  --repo-path /repo --output /repo/review.md
```

## Publishing to Docker Hub

Login to Docker Hub:

```bash
docker login
```

Push the image:

```bash
docker push kirill89/reviewcerberus-cli:latest
docker push kirill89/reviewcerberus-cli:0.1.0
```

Or use buildx to build and push in one command:

```bash
docker buildx build --platform linux/amd64,linux/arm64 \
  -t kirill89/reviewcerberus-cli:latest \
  -t kirill89/reviewcerberus-cli:0.1.0 \
  --push .
```

## Versioning

When releasing a new version:

1. Update version in `pyproject.toml`
2. Build and tag with version number:

```bash
docker buildx build --platform linux/amd64,linux/arm64 \
  -t kirill89/reviewcerberus-cli:latest \
  -t kirill89/reviewcerberus-cli:X.Y.Z \
  --push .
```
