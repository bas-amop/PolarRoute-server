.DEFAULT_GOAL := help
RABBITMQ_CONTAINER := "prs-rabbitmq"

define BROWSER_PYSCRIPT
import os, webbrowser, sys
try:
	from urllib import pathname2url
except:
	from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT
BROWSER := python -c "$$BROWSER_PYSCRIPT"

# .PHONY: clean-coverage
# clean-coverage: ## Remove coverage reports
# 	@echo "+ $@"
# 	@rm -rf htmlcov/
# 	@rm -rf .coverage
# 	@rm -rf coverage.xml

.PHONY: clean-pytest
clean-pytest: ## Remove pytest cache
	@echo "+ $@"
	@rm -rf .pytest_cache/

.PHONY: clean-docs-build
clean-docs-build: ## Remove local docs
	@echo "+ $@"
	@rm -rf docs/_build

.PHONY: clean-pyc
clean-pyc: ## Remove Python file artifacts
	@echo "+ $@"
	@find . -type d -name '__pycache__' -exec rm -rf {} +
	@find . -type f -name '*.py[co]' -exec rm -f {} +
	@find . -name '*~' -exec rm -f {} +

.PHONY: clean ## Remove all file artifacts
clean: clean-build clean-pyc clean-pytest clean-docs-build

.PHONY: lint
lint: ## Check code style
	@echo "+ $@"
	@ruff check

.PHONY: test
test: ## Run tests quickly with the default Python
	@echo "+ $@"
	@pytest

# .PHONY: docs
# docs: ## Generate Sphinx HTML documentation, including API docs
# 	@echo "+ $@"
# 	@tox -e docs
# 	@$(BROWSER) docs/_build/html/index.html

# .PHONY: servedocs
# servedocs: ## Rebuild docs automatically
# 	@echo "+ $@"
# 	@tox -e servedocs

.PHONY: migrate
migrate: ## Apply database migrations (or create for first time)
	@echo "+ $@"
	@python manage.py migrate

.PHONY: migrations
migrations: ## Create database migration files from changes to models
	@echo "+ $@"
	@python manage.py makemigrations

.PHONY: start-dev-server
start-dev-server: ## start Django dev server
	@echo "+ $@"
	@python manage.py runserver

.PHONY: start-celery
start-celery: ## Start celery
	@echo "+ $@"
	@celery -A polarrouteserver worker -l INFO &

.PHONY: stop-celery
stop-celery: ## Stop celery
	@echo "+ $@"
	@pkill -9 -f 'celery -A polarrouteserver worker'

.PHONY: start-rabbitmq
start-rabbitmq: ## Start rabbitmq via docker
	@echo "+ $@"
	@docker run -d -p 5672:5672 --name ${RABBITMQ_CONTAINER} rabbitmq

.PHONY: stop-rabbitmq
stop-rabbitmq: ## Stop rabbitmq docker container
	@echo "+ $@"
	@docker stop ${RABBITMQ_CONTAINER}
	@docker rm ${RABBITMQ_CONTAINER}

.PHONY: serve-dev
export DJANGO_SETTINGS_MODULE=polarrouteserver.settings.development
serve-dev: start-rabbitmq start-celery start-dev-server ## Run all the components for serving a development instance.

.PHONY: help
help:
	@echo "Note: Remember to activate your virtual environment (if used)."
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'

