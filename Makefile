.PHONY: test lint format docker-build docker-build-push

test:
	poetry run pytest -v

lint:
	poetry run mypy src tests
	poetry run isort --check-only src tests
	poetry run black --check src tests
	find . -name '*.md' -not -path './.pytest_cache/*' -not -path './.venv/*' -print0 | xargs -0 poetry run mdformat --check --compact-tables --wrap 80 --number
	poetry run autoflake --check --remove-all-unused-imports --remove-unused-variables --recursive src tests

format:
	poetry run autoflake --in-place --remove-all-unused-imports --remove-unused-variables --recursive src tests
	find . -name '*.md' -not -path './.pytest_cache/*' -not -path './.venv/*' -print0 | xargs -0 poetry run mdformat --compact-tables --wrap 80 --number
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
