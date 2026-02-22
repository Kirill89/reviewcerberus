.PHONY: install test lint format docker-build docker-build-push

install:
	poetry install
	cd action && npm ci
	cd act-test && npm ci

test:
	poetry run pytest -v --ignore=tests/test_integration.py
	cd action && npm test
	cd act-test && npm ci && npm test

lint:
	poetry run mypy src tests
	poetry run isort --check-only src tests
	poetry run black --check src tests
	find . -name '*.md' -not -path './.pytest_cache/*' -not -path './.venv/*' -not -path './action/node_modules/*' -not -path './act-test/node_modules/*' -print0 | xargs -0 poetry run mdformat --check --compact-tables --wrap 80 --number
	poetry run autoflake --check --remove-all-unused-imports --remove-unused-variables --recursive src tests
	cd action && npm run format:check
	cd action && npm run lint
	cd act-test && npm run format:check
	cd act-test && npm run lint

format:
	poetry run autoflake --in-place --remove-all-unused-imports --remove-unused-variables --recursive src tests
	find . -name '*.md' -not -path './.pytest_cache/*' -not -path './.venv/*' -not -path './action/node_modules/*' -not -path './act-test/node_modules/*' -print0 | xargs -0 poetry run mdformat --compact-tables --wrap 80 --number
	poetry run isort src tests
	poetry run black src tests
	cd action && npm run format
	cd act-test && npm run format

docker-build:
	docker build -t kirill89/reviewcerberus:latest .

docker-build-push:
	$(eval VERSION := $(shell poetry version -s))
	docker buildx build --platform linux/amd64,linux/arm64 \
		-t kirill89/reviewcerberus:latest \
		-t kirill89/reviewcerberus:$(VERSION) \
		-t kirill89/reviewcerberus-cli:latest \
		-t kirill89/reviewcerberus-cli:$(VERSION) \
		--push .
