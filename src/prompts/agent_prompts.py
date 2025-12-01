"""Aggregated exports for all agent prompts.

This module preserves the original import surface while delegating the prompt
definitions to smaller files so each agent can be debugged independently.
"""

from .understanding import (
    UNDERSTANDING_AGENT_SYSTEM,
    get_understanding_prompt,
)
from .customer import (
    CUSTOMER_AGENT_SYSTEM,
    get_customer_prompt,
)
from .traffic import (
    TRAFFIC_AGENT_SYSTEM,
    get_traffic_prompt,
)
from .competition import (
    COMPETITION_AGENT_SYSTEM,
    get_competition_prompt,
)
from .weighting import (
    WEIGHTING_AGENT_SYSTEM,
    get_weighting_prompt,
)
from .evaluation import (
    EVALUATION_AGENT_SYSTEM,
    EVALUATION_SEPARATE_AGENT_SYSTEM,
    get_evaluation_prompt,
)
from .final_report import (
    FINAL_REPORT_AGENT_SYSTEM,
    get_final_report_prompt,
)

__all__ = [
    "UNDERSTANDING_AGENT_SYSTEM",
    "CUSTOMER_AGENT_SYSTEM",
    "TRAFFIC_AGENT_SYSTEM",
    "COMPETITION_AGENT_SYSTEM",
    "WEIGHTING_AGENT_SYSTEM",
    "EVALUATION_AGENT_SYSTEM",
    "FINAL_REPORT_AGENT_SYSTEM",
    "get_understanding_prompt",
    "get_customer_prompt",
    "get_traffic_prompt",
    "get_competition_prompt",
    "get_weighting_prompt",
    "get_evaluation_prompt",
    "get_final_report_prompt",
]
