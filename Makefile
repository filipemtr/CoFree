.PHONY: up down logs test lint migrate clean
up:
	docker compose up --build -d
migrate:
	docker compose run --rm migrate
logs:
	docker compose logs -f --tail=100
down:
	docker compose down
test:
	cd backend && python -m pytest -q
lint:
	cd backend && python -m ruff check app tests
clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
