"""
This package initializes the database module for the Nutrition Tracker backend.
It exposes the Supabase client factory function so all other backend modules can
import a pre-configured client without needing to repeat connection setup code.
When fully implemented, it may also handle connection pooling, retry logic, and
centralized error handling for all database operations across the application.
"""

from .supabase_client import get_supabase_client
