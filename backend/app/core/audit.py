"""
Audit logging for security-critical operations.

Logs all authentication, authorization, and sensitive business events
for compliance, investigation, and monitoring purposes.

LOGGING SENSITIVE DATA: All auth-related logs mask passwords and tokens.
"""
import logging
import json
from datetime import datetime
from typing import Any, Optional, Dict
from app.models.user import User

# Separate logger for audit events (can be shipped to centralized logging)
audit_logger = logging.getLogger("audit")


class AuditLog:
    """Central audit logging for security-critical events."""

    @staticmethod
    def log_authentication(
        action: str,  # "login", "logout", "register", "failed_login"
        email: str,
        ip_address: str,
        success: bool,
        reason: str = "",
    ):
        """
        Log authentication events.
        
        SECURITY: Logs include IP address for failed login detection,
        but don't include passwords or tokens.
        
        Usage:
            AuditLog.log_authentication("login", "user@example.com", "192.168.1.1", True)
            AuditLog.log_authentication("failed_login", "user@example.com", "192.168.1.1", False, reason="Invalid password")
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": f"auth.{action}",
            "email": email,
            "ip_address": ip_address,
            "success": success,
        }
        
        if reason and not success:
            log_entry["reason"] = reason
        
        audit_logger.info(json.dumps(log_entry))

    @staticmethod
    def log_action(
        action: str,  # "create", "approve", "reject", "delete", "update"
        resource_type: str,  # "invoice", "inventory", "agent_action", "agent_action", "business"
        resource_id: int,
        user: User,
        changes: Optional[Dict[str, Any]] = None,
    ):
        """
        Log business-critical actions.
        
        SECURITY: Each change to important resources is logged with:
        - Who made the change (user ID + email)
        - What changed (resource type and ID)
        - When (timestamp)
        - What changed (for audits)
        
        Usage:
            AuditLog.log_action("approve", "agent_action", 123, current_user)
            AuditLog.log_action("delete", "inventory", 456, current_user, changes={"item": "Paracetamol"})
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": f"{resource_type}.{action}",
            "user_id": user.id,
            "user_email": user.email,
            "resource_id": resource_id,
        }
        
        if changes:
            log_entry["changes"] = changes
        
        audit_logger.info(json.dumps(log_entry))

    @staticmethod
    def log_access_denied(
        action: str,  # "read", "write", "delete", "approve"
        resource_type: str,  # "invoice", "inventory", "agent_action"
        resource_id: int,
        user_id: int,
        reason: str,
    ):
        """
        Log denied access attempts (potential attacks).
        
        SECURITY: Track unauthorized access patterns:
        - User trying to access other users' invoices (IDOR)
        - Attempting forbidden operations
        - Suspicious activity patterns
        
        Usage:
            AuditLog.log_access_denied("read", "invoice", 456, 1, "Different business")
            AuditLog.log_access_denied("approve", "agent_action", 789, 2, "Not action owner")
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_severity": "WARNING",
            "event_type": "access_denied",
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "user_id": user_id,
            "reason": reason,
        }
        
        audit_logger.warning(json.dumps(log_entry))

    @staticmethod
    def log_failed_login_attempt(
        email: str,
        ip_address: str,
        attempt_count: int = 1,
    ):
        """
        Log failed login attempts for brute-force detection.
        
        SECURITY: Monitor for:
        - Multiple failed attempts from same IP
        - Distributed attacks across IPs
        - Specific email targeting
        
        Usage:
            AuditLog.log_failed_login_attempt("user@example.com", "192.168.1.100", attempt_count=3)
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "auth.failed_login_attempt",
            "email": email,
            "ip_address": ip_address,
            "attempt_count": attempt_count,
        }
        
        audit_logger.warning(json.dumps(log_entry))

    @staticmethod
    def log_permission_change(
        user_id: int,
        granted_by: int,
        permission: str,
        granted: bool,
    ):
        """
        Log permission/role changes.
        
        SECURITY: Track who changed permissions for who.
        Helps detect unauthorized privilege escalation.
        
        Usage:
            AuditLog.log_permission_change(user_id=2, granted_by=1, permission="admin", granted=True)
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "permissions.changed",
            "user_id": user_id,
            "granted_by": granted_by,
            "permission": permission,
            "granted": granted,
        }
        
        audit_logger.info(json.dumps(log_entry))

    @staticmethod
    def log_api_call(
        endpoint: str,
        method: str,
        user_id: Optional[int] = None,
        ip_address: str = "",
        status_code: int = 200,
        duration_ms: float = 0,
    ):
        """
        Log API calls for performance and security monitoring.
        
        SECURITY: Can detect:
        - Unusual access patterns
        - Performance issues (potential DoS)
        - Unauthenticated access attempts
        
        Usage:
            AuditLog.log_api_call("/records/invoices", "GET", user_id=1, ip_address="192.168.1.1", status_code=200, duration_ms=45.3)
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "api.call",
            "endpoint": endpoint,
            "method": method,
            "user_id": user_id,
            "ip_address": ip_address,
            "status_code": status_code,
            "duration_ms": duration_ms,
        }
        
        audit_logger.info(json.dumps(log_entry))

    @staticmethod
    def log_security_event(
        event_type: str,  # "password_reset", "mfa_enabled", "token_revoked", etc.
        user_id: int,
        details: Optional[str] = None,
    ):
        """
        Log security-related events.
        
        SECURITY: Track security posture changes.
        
        Usage:
            AuditLog.log_security_event("password_reset", user_id=1, details="Via email link")
            AuditLog.log_security_event("mfa_enabled", user_id=1)
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": f"security.{event_type}",
            "user_id": user_id,
        }
        
        if details:
            log_entry["details"] = details
        
        audit_logger.info(json.dumps(log_entry))
