"""Role-Based Access Control — permissions, roles, membership management."""

from dataclasses import dataclass, field
from enum import Enum


class Permission(str, Enum):
    VIEW_REVIEWS = "view_reviews"
    CREATE_REVIEW = "create_review"
    MANAGE_REPOS = "manage_repos"
    MANAGE_TEAM = "manage_team"
    ADMIN = "admin"


@dataclass
class Role:
    name: str
    permissions: set[Permission] = field(default_factory=set)

    def has_permission(self, permission: Permission) -> bool:
        return permission in self.permissions or Permission.ADMIN in self.permissions


# Predefined roles
ROLES = {
    "owner": Role("owner", {
        Permission.VIEW_REVIEWS, Permission.CREATE_REVIEW,
        Permission.MANAGE_REPOS, Permission.MANAGE_TEAM,
        Permission.ADMIN,
    }),
    "admin": Role("admin", {
        Permission.VIEW_REVIEWS, Permission.CREATE_REVIEW,
        Permission.MANAGE_REPOS, Permission.MANAGE_TEAM,
        Permission.ADMIN,
    }),
    "member": Role("member", {
        Permission.VIEW_REVIEWS, Permission.CREATE_REVIEW,
    }),
    "viewer": Role("viewer", {
        Permission.VIEW_REVIEWS,
    }),
}


@dataclass
class Membership:
    user_id: str
    organization_id: str
    role: str  # "owner" | "admin" | "member" | "viewer"

    def get_role(self) -> Role:
        return ROLES.get(self.role, ROLES["viewer"])

    def can(self, permission: Permission) -> bool:
        return self.get_role().has_permission(permission)


class AccessControl:
    """Central access control manager for organizations and teams."""

    def __init__(self):
        self._memberships: dict[str, list[Membership]] = {}  # org_id -> [memberships]

    def add_member(self, org_id: str, user_id: str, role: str = "member"):
        if org_id not in self._memberships:
            self._memberships[org_id] = []
        # Update existing or add new
        for m in self._memberships[org_id]:
            if m.user_id == user_id:
                m.role = role
                return
        self._memberships[org_id].append(Membership(user_id, org_id, role))

    def remove_member(self, org_id: str, user_id: str):
        if org_id in self._memberships:
            self._memberships[org_id] = [
                m for m in self._memberships[org_id] if m.user_id != user_id
            ]

    def get_membership(self, org_id: str, user_id: str) -> Membership | None:
        for m in self._memberships.get(org_id, []):
            if m.user_id == user_id:
                return m
        return None

    def check(self, org_id: str, user_id: str,
              permission: Permission) -> bool:
        m = self.get_membership(org_id, user_id)
        if m is None:
            return False
        return m.can(permission)

    def list_members(self, org_id: str) -> list[Membership]:
        return self._memberships.get(org_id, [])


# Singleton
_default_access_control = AccessControl()


def check_permission(org_id: str, user_id: str,
                     permission: Permission) -> bool:
    return _default_access_control.check(org_id, user_id, permission)
