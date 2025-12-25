.PHONY: test lint format docker-build docker-build-push

test:
	poetry run pytest -v

lint:
	poetry run mypy src tests
	poetry run isort --check-only src tests
	poetry run black --check src tests
	poetry run mdformat --check --compact-tables --wrap 80 --number README.md DOCKER.md spec/*.md src/agent/prompts/*.md

format:
	poetry run mdformat --compact-tables --wrap 80 --number README.md DOCKER.md spec/*.md src/agent/prompts/*.md
	poetry run isort src tests
	poetry run black src tests

docker-build:
	docker build -t kirill89/reviewcerberus-cli:latest .

docker-build-push:
	$(eval VERSION := $(shell poetry version -s))
	docker buildx build --platform linux/amd64,linux/arm64 \
		-t kirill89/reviewcerberus-cli:latest \
		-t kirill89/reviewcerberus-cli:$(VERSION) \
		--push .
