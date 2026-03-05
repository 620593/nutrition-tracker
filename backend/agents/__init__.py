"""
This package initializes the agents module for the Nutrition Tracker LangGraph system.
It exposes the compiled LangGraph workflow and the shared AgentState so that external
modules can import and invoke the agent pipeline cleanly. When fully implemented, it
will also handle graph compilation configuration and optional tracing setup.
"""

from .graph import nutrition_graph
from .state import NutritionState
