"""LookML Dashboard Generator supporting Vertex AI Gemini."""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional
import yaml

from app.config import settings
from app.skills_loader import LookMLSkillsKnowledgeBase

logger = logging.getLogger(__name__)


class LookMLDashboardGenerator:
    """Generates LookML dashboards dynamically using Vertex AI Gemini."""

    def __init__(
        self,
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        skills_dir: Optional[str] = None,
    ):
        self.project_id = (
            project_id
            or settings.google_cloud_project
            or os.environ.get("VERTEXAI_PROJECT")
            or os.environ.get("GOOGLE_CLOUD_PROJECT")
        )
        self.location = location or settings.vertexai_location or "global"
        self.knowledge_base = LookMLSkillsKnowledgeBase(skills_dir)
        self._system_prompt = self.knowledge_base.compile_full_system_prompt()
        self._gemini_client = None

    @property
    def loaded_skills_summary(self) -> Dict[str, int]:
        return self.knowledge_base.get_summary()

    def _get_gemini_client(self):
        if self._gemini_client is None:
            try:
                from google import genai
                self._gemini_client = genai.Client(
                    vertexai=True,
                    project=self.project_id,
                    location=self.location,
                )
            except Exception as e:
                logger.warning("Failed to initialize google.genai Client: %s. Falling back to vertexai SDK.", e)
                import vertexai
                vertexai.init(project=self.project_id, location=self.location)
                self._gemini_client = "vertexai_sdk"
        return self._gemini_client

    def generate(
        self,
        prompt: str,
        explore_metadata: Dict[str, Any],
        dashboard_title: Optional[str] = None,
        preferred_slug: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> str:
        """Generate LookML dashboard YAML grounded on Explore schema."""
        target_model = model_name or settings.llm_model or "gemini-3.6-flash"
        model = explore_metadata["model"]
        explore = explore_metadata["explore"]
        dimensions = explore_metadata.get("dimensions", [])
        measures = explore_metadata.get("measures", [])
        filters = explore_metadata.get("filters", [])
        parameters = explore_metadata.get("parameters", [])

        dim_list = [f"  - {d.get('name')} (type: {d.get('type')}, label: \"{d.get('label')}\")" for d in dimensions]
        meas_list = [f"  - {m.get('name')} (type: {m.get('type')}, label: \"{m.get('label')}\")" for m in measures]
        filter_list = [f"  - {f.get('name')} (label: \"{f.get('label')}\")" for f in filters] if filters else []
        param_list = [f"  - {p.get('name')} (label: \"{p.get('label')}\")" for p in parameters] if parameters else []

        user_content = f"""USER DASHBOARD REQUEST:
{prompt}

CONTEXT & SCHEMA:
- LookML Model: {model}
- LookML Explore: {explore}
- Proposed Title: {dashboard_title or 'Auto-generated'}
{f'- Preferred Slug (for in-place update): {preferred_slug}' if preferred_slug else ''}

VERIFIED EXPLORE FIELDS:
=== MEASURES ({len(measures)}) ===
{chr(10).join(meas_list) if meas_list else '  (None)'}

=== DIMENSIONS ({len(dimensions)}) ===
{chr(10).join(dim_list) if dim_list else '  (None)'}
"""
        if filter_list:
            user_content += f"\n=== FILTER-ONLY FIELDS ===\n{chr(10).join(filter_list)}\n"
        if param_list:
            user_content += f"\n=== PARAMETERS ===\n{chr(10).join(param_list)}\n"

        if preferred_slug:
            user_content += f"\nIMPORTANT: Set `preferred_slug: \"{preferred_slug}\"` under the top-level `- dashboard:` declaration."

        user_content += "\nGenerate the complete, production-ready LookML Dashboard YAML for this request. Strictly follow all layout, element, table calculation, and filter listener specifications from the system instructions."

        raw_text = self._call_model(target_model, user_content)

        yaml_content = self._extract_yaml(raw_text)
        if preferred_slug and "preferred_slug:" not in yaml_content:
            from app.importer import inject_preferred_slug
            yaml_content = inject_preferred_slug(yaml_content, preferred_slug)

        self._validate_yaml(yaml_content)
        return yaml_content

    def generate_edit(
        self,
        current_lookml: str,
        edit_instructions: str,
        explore_metadata: Dict[str, Any],
        preferred_slug: str,
        model_name: Optional[str] = None,
    ) -> str:
        """Modify an existing LookML dashboard YAML based on user edit instructions."""
        target_model = model_name or settings.llm_model or "gemini-3.6-flash"
        model = explore_metadata["model"]
        explore = explore_metadata["explore"]
        dimensions = explore_metadata.get("dimensions", [])
        measures = explore_metadata.get("measures", [])

        dim_list = [f"  - {d.get('name')} (type: {d.get('type')}, label: \"{d.get('label')}\")" for d in dimensions]
        meas_list = [f"  - {m.get('name')} (type: {m.get('type')}, label: \"{m.get('label')}\")" for m in measures]

        user_content = f"""USER EDIT INSTRUCTIONS:
{edit_instructions}

CURRENT LOOKML DASHBOARD TO MODIFY:
```yaml
{current_lookml}
```

CONTEXT & SCHEMA:
- LookML Model: {model}
- LookML Explore: {explore}
- Required Preferred Slug: {preferred_slug}

VERIFIED EXPLORE FIELDS:
=== MEASURES ===
{chr(10).join(meas_list)}

=== DIMENSIONS ===
{chr(10).join(dim_list)}

Apply the requested modifications to the dashboard. Preserve the newspaper layout, existing functional tiles (unless asked to change), and ensure `preferred_slug: "{preferred_slug}"` remains set under `- dashboard:`. Output the complete updated LookML YAML."""

        raw_text = self._call_model(target_model, user_content)

        yaml_content = self._extract_yaml(raw_text)
        from app.importer import inject_preferred_slug
        yaml_content = inject_preferred_slug(yaml_content, preferred_slug)
        self._validate_yaml(yaml_content)
        return yaml_content

    def _call_model(self, model_name: str, user_content: str) -> str:
        """Generate response via Vertex AI Gemini."""
        client = self._get_gemini_client()
        if client == "vertexai_sdk":
            from vertexai.generative_models import GenerativeModel
            gmodel = GenerativeModel(model_name, system_instruction=self._system_prompt)
            resp = gmodel.generate_content(user_content)
            return resp.text
        else:
            resp = client.models.generate_content(
                model=model_name,
                contents=user_content,
                config={"system_instruction": self._system_prompt},
            )
            return resp.text

    def _extract_yaml(self, text: str) -> str:
        """Extract YAML block from LLM response."""
        match = re.search(r"```(?:yaml|lookml)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            return match.group(1).strip()

        cleaned = text.strip()
        if cleaned.startswith("```yaml"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```lookml"):
            cleaned = cleaned[9:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return cleaned.strip()

    def _validate_yaml(self, yaml_str: str) -> None:
        """Validate YAML syntax and structure."""
        try:
            parsed = yaml.safe_load(yaml_str)
            if not isinstance(parsed, list) or len(parsed) == 0:
                raise ValueError("LookML dashboard must be a YAML list starting with '- dashboard: ...'")
            if "dashboard" not in parsed[0]:
                raise ValueError("First element in LookML dashboard YAML must have 'dashboard' key")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax generated: {e}")
