"""
Blackbaud API Python SDK

A unified library for interacting with the Blackbaud API.
"""

from .client import BlackbaudOAuth
from .auth import authenticate_interactive, authenticate_automation

__all__ = [
    'BlackbaudOAuth',
    'authenticate_interactive',
    'authenticate_automation'
]
