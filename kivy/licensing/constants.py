"""
Licensing Constants and Configuration for Sketch Animation Studio (Program B).
Zero-Trust Architecture: Scoped strictly to application_slug = 'sketch_animation'.
"""

import os
import sys

# Fixed Supabase Project URL
SUPABASE_URL = "https://ixkcnbreiuaaujozmczp.supabase.co"

# Real Supabase Anon Gateway Key
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml4a2NuYnJlaXVhYXVqb3ptY3pwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODU1OTA4ODIsImV4cCI6MjEwMTE2Njg4Mn0."
    "p4hJMuKietVz6H5zjuBxbZJj3hyAQw3zu60H9FbzA9g"
)

# Application Identity Scope (Permanent Isolation)
APPLICATION_SLUG = "sketch_animation"
APPLICATION_NAME = "Sketch Animation Studio"
APP_VERSION = "2.0.0"

# Secret HMAC Salt for Client-Server Integrity
_SALT_PARTS = ["ScenariosPro_", "Client_HMAC_", "Secret_Salt_", "2026_v1"]
CLIENT_SECRET_SALT = "".join(_SALT_PARTS)

# Endpoints
ENDPOINT_VERIFY = f"{SUPABASE_URL}/functions/v1/verify-license"
ENDPOINT_ACTIVATE = f"{SUPABASE_URL}/functions/v1/activate-machine"
ENDPOINT_HEARTBEAT = f"{SUPABASE_URL}/functions/v1/heartbeat"
ENDPOINT_CHECK_UPDATE = f"{SUPABASE_URL}/functions/v1/check-update"

# Heartbeat Interval (Seconds) - Strict Online Policy
HEARTBEAT_INTERVAL_SECONDS = 120
