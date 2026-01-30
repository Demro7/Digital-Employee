"""
Authentication Module for Digital Employee System.

This module provides JWT-based authentication and role-based access control (RBAC).

Features:
    - JWT token generation and validation
    - Route protection decorators
    - Role-based access control (customer, accounting)
    - Session fallback for authentication

Configuration:
    JWT_SECRET: Secret key for signing tokens (from .env)
    JWT_EXPIRATION_HOURS: Token validity period (default: 24 hours)
"""

import os
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, session
from dotenv import load_dotenv

load_dotenv()

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    import warnings
    warnings.warn(
        "JWT_SECRET not set! Using auto-generated secret. "
        "Set JWT_SECRET in .env for production!",
        UserWarning
    )
    JWT_SECRET = os.urandom(32).hex()

JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24


def generate_token(user: dict) -> str:
    """
    Generate JWT token for authenticated user.
    
    Args:
        user: User dictionary with _id, username, role, and business_name.
        
    Returns:
        str: Encoded JWT token.
    """
    payload = {
        "user_id": user["_id"],
        "username": user["username"],
        "role": user["role"],
        "business_name": user.get("business_name", ""),
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and validate JWT token.
    
    Args:
        token: JWT token string.
        
    Returns:
        dict: Result with 'success' boolean and either 'payload' or 'error'.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {"success": True, "payload": payload}
    except jwt.ExpiredSignatureError:
        return {"success": False, "error": "Token has expired"}
    except jwt.InvalidTokenError:
        return {"success": False, "error": "Invalid token"}


def get_current_user() -> dict | None:
    """
    Get current user from request token or session.
    
    Checks Authorization header first, then falls back to session.
    
    Returns:
        dict | None: User payload if authenticated, None otherwise.
    """
    # Try token from header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        result = decode_token(token)
        if result["success"]:
            return result["payload"]
    
    # Try token from session
    if "user" in session:
        return session["user"]
    
    return None


def login_required(f):
    """
    Decorator to require authentication for a route.
    
    Returns 401 Unauthorized if no valid token/session.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function


def role_required(allowed_roles: list):
    """
    Decorator factory to require specific role(s) for route access.
    
    Args:
        allowed_roles: List of role strings that can access the route.
        
    Returns:
        Decorator that enforces role-based access.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({"error": "Authentication required"}), 401
            
            if user.get("role") not in allowed_roles:
                return jsonify({"error": "Access denied. Insufficient permissions."}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def customer_only(f):
    """Decorator to restrict route access to customers (sales users) only."""
    return role_required(["customer"])(f)


def accounting_only(f):
    """Decorator to restrict route access to accounting staff only."""
    return role_required(["accounting"])(f)


def any_authenticated(f):
    """Decorator alias for login_required - allows any authenticated user."""
    return login_required(f)
