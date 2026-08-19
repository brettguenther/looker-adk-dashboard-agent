-include .env
export

.PHONY: install setup-oauth register-oauth-client deploy deploy-no-wait deploy-status register-adk patch-adk test-local clean

install:
	pip install -e .

register-oauth-client:
	python3 scripts/create_looker_oauth_client.py

setup-oauth:
	python3 scripts/ge_oauth_deployment.py

deploy:
	agents-cli deploy -d agent_runtime --project $(GOOGLE_CLOUD_PROJECT) --region $(GOOGLE_CLOUD_LOCATION) --service-name $(AGENT_ID) --no-confirm-project

deploy-no-wait:
	agents-cli deploy -d agent_runtime --project $(GOOGLE_CLOUD_PROJECT) --region $(GOOGLE_CLOUD_LOCATION) --service-name $(AGENT_ID) --no-confirm-project --no-wait

deploy-status:
	agents-cli deploy --status

register-adk:
	python3 scripts/register_adk_agent.py --action create

patch-adk:
	python3 scripts/register_adk_agent.py --action patch

test-local:
	python3 scripts/local_runner.py

web:
	adk web --port 8000 .

playground:
	agents-cli playground

preview:
	python3 scripts/preview_server.py --dashboard-id $(or $(DASHBOARD_ID),1)

clean:
	rm -rf dist build *.egg-info app/*.egg-info
