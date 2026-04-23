# ─────────────────────────────────────────────────────────────────────────────
#  ReqRes QA Automation — Makefile
#
#  Provides short aliases for the most common developer tasks.
#  All commands delegate to pytest or playwright — no magic here.
#
#  Usage:  make <target>
#  List:   make help
# ─────────────────────────────────────────────────────────────────────────────

.DEFAULT_GOAL := help
.PHONY: help install install-browsers smoke test test-get test-post \
        test-put test-delete test-negative test-mock test-crud \
        report clean

# ── Setup ─────────────────────────────────────────────────────────────────────

install:                       ## Install all Python dependencies
	pip install -e ".[dev]"

install-browsers:              ## Install Playwright Chromium browser
	playwright install chromium --with-deps

setup: install install-browsers ## Full setup from scratch (install + browsers)

# ── Test targets ──────────────────────────────────────────────────────────────

smoke:                         ## Run smoke tests only (fast sanity check)
	pytest tests/test_smoke.py -v --tb=short

test-get:                      ## Run GET /users tests
	pytest tests/test_get_users.py -v --tb=short

test-post:                     ## Run POST /users, /login, /register tests
	pytest tests/test_post_users.py -v --tb=short

test-put:                      ## Run PUT and PATCH /users tests
	pytest tests/test_put_patch_users.py -v --tb=short

test-delete:                   ## Run DELETE /users tests
	pytest tests/test_delete_users.py -v --tb=short

test-crud:                     ## Run full CRUD suite (GET + POST + PUT + DELETE)
	pytest tests/test_get_users.py tests/test_post_users.py \
	       tests/test_put_patch_users.py tests/test_delete_users.py \
	       -v --tb=short

test-negative:                 ## Run negative and edge case tests
	pytest tests/test_negative.py -v --tb=short

test-mock:                     ## Run mock/mocking tests (no internet required)
	pytest tests/test_mock_errors.py -v --tb=short

test:                          ## Run the full test suite (all 208 tests)
	pytest tests/ -v --tb=short

test-parallel:                 ## Run full suite in parallel (4 workers)
	pytest tests/ -n 4 --tb=short

# ── Reporting ─────────────────────────────────────────────────────────────────

report:                        ## Open the HTML report in the default browser
	@python -c "import webbrowser, os; webbrowser.open('file://' + os.path.abspath('reports/report.html'))"

allure-serve:                  ## Generate and serve Allure report locally
	allure serve allure-results/

# ── Maintenance ───────────────────────────────────────────────────────────────

clean:                         ## Remove generated files (reports, cache, __pycache__)
	rm -rf reports/ allure-results/ allure-report/ .pytest_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

lint:                          ## Check for syntax errors across all Python files
	python -m py_compile \
	    config/settings.py \
	    clients/api_client.py \
	    models/user.py \
	    models/auth.py \
	    utils/assertions.py \
	    tests/conftest.py \
	    tests/test_smoke.py \
	    tests/test_get_users.py \
	    tests/test_post_users.py \
	    tests/test_put_patch_users.py \
	    tests/test_delete_users.py \
	    tests/test_negative.py \
	    tests/test_mock_errors.py
	@echo "All files OK"

# ── Help ──────────────────────────────────────────────────────────────────────

help:                          ## Show this help message
	@echo ""
	@echo "ReqRes QA Automation — available targets:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	    | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""