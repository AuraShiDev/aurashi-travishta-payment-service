from __future__ import annotations

from fastapi import Path
from jinja2 import Environment, FileSystemLoader


TEMPLATES_DIR = "app/invoices/templates"
env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))


def render_template(template_name: str, context: dict) -> str:
    template = env.get_template(template_name)
    return template.render(context)
