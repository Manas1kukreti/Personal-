from functools import lru_cache
from pathlib import Path

import yaml


CONFIG_PATH = Path(__file__).parent / "project_config.yml"


@lru_cache(maxsize=1)
def load_project_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file) or {}


def get_config_section(section_name, default=None):
    config = load_project_config()
    return config.get(section_name, default or {})


def get_workflow_config():
    return get_config_section("workflow")


def get_agent_config(agent_name):
    agents = get_config_section("agents")
    return agents.get(agent_name, {})


def get_excel_reader_config():
    return get_config_section("excel_reader")


def get_field_mapping_config():
    return get_config_section("field_mapping")


def get_relation_mapping_config():
    return get_config_section("relation_mapping")


def get_financial_logic_config():
    return get_config_section("financial_logic")
