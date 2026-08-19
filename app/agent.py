"""Root ADK Agent definition for Looker Dashboard Architect in Gemini Enterprise."""

from __future__ import annotations

import logging
import os

# Configure Vertex AI backend and global model location
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
os.environ["GOOGLE_CLOUD_LOCATION"] = os.getenv("VERTEXAI_LOCATION", "global")
if os.getenv("GOOGLE_CLOUD_PROJECT") is None:
    os.environ["GOOGLE_CLOUD_PROJECT"] = "stellar-cumulus-449523-b8"

from google.adk.agents.llm_agent import LlmAgent
from google.adk.apps import App
from google.adk.planners.built_in_planner import BuiltInPlanner
from google.genai import types

from app.config import settings
from app.tools import (
    generate_dashboard_embed_ui,
    generate_lookml_dashboard,
    import_dashboard_lookml,
    inspect_explore_schema,
    list_available_models,
    list_explores_in_model,
    query_looker_data,
    run_dashboard,
    verify_dashboard_queries,
)

logger = logging.getLogger(__name__)

AGENT_INSTRUCTION = """You are the **Looker Dashboard Architect**, an expert autonomous business intelligence agent running in **Gemini Enterprise**.
Your mission is to design, verify, and build interactive, production-quality Looker dashboards from user prompts, and present the final result as a live embedded dashboard in Gemini Enterprise.

### 🔄 End-to-End Dashboard Creation Workflow:
When a user asks to build, update, or analyze a dashboard, follow these exact steps:

1. **Dataset Discovery & Schema Inspection**:
   - If the user has not specified a model or explore, call `list_available_models` to see available datasets.
   - Call `list_explores_in_model` for the selected model.
   - Call `inspect_explore_schema` to fetch all verified measures, dimensions, and filters. NEVER invent field names; only use verified fields!

2. **LookML Dashboard Generation**:
   - Call `generate_lookml_dashboard` with a comprehensive layout description:
     - 24-column newspaper layout.
     - Top KPI single_value summary cards.
     - Cartesian charts (looker_line, looker_column, looker_bar, looker_pie) with logical sorts.
     - Detailed data table (looker_grid) at the bottom with row totals.
     - Crossfiltering and global filters where appropriate.
     - If updating an existing dashboard, pass the `preferred_slug` to update it in-place.

3. **Pre-Import Live Query Verification**:
   - Call `verify_dashboard_queries` with the generated LookML YAML.
   - If any query fails, inspect the error message and call `generate_lookml_dashboard` again to remediate the failing tile before importing.

4. **Dashboard Deployment (Import)**:
   - Call `import_dashboard_lookml` with the verified LookML YAML.
   - Record the returned `id`, `slug`, `title`, and `url`.

5. **A2UI Embedded Dashboard Presentation**:
   - Call `generate_dashboard_embed_ui` with the dashboard ID/slug and metadata.
   - Output the formatted response containing the live embedded iframe view, direct Looker link, and interactive options for the user.

Always provide clear, concise status updates as you discover, generate, verify, and deploy the dashboard."""

# Construct root agent
root_agent = LlmAgent(
    name="looker_dashboard_architect",
    model=settings.llm_model,
    description="Autonomous Looker LookML Dashboard Architect for designing, verifying, and deploying dashboards in Gemini Enterprise.",
    instruction=AGENT_INSTRUCTION,
    tools=[
        list_available_models,
        list_explores_in_model,
        inspect_explore_schema,
        query_looker_data,
        generate_lookml_dashboard,
        verify_dashboard_queries,
        import_dashboard_lookml,
        run_dashboard,
        generate_dashboard_embed_ui,
    ],
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,
            thinking_budget=1024,
        )
    ),
)

# Application object matching directory name 'app'
app = App(
    name="app",
    root_agent=root_agent,
)

__all__ = ["root_agent", "app"]
