"""Tests for RBAC access control."""

from src.auth.rbac import (
    Permission, Role, Membership, AccessControl, ROLES, check_permission,
)


class TestPermission:
    def test_all_permissions_defined(self):
        assert Permission.VIEW_REVIEWS.value == "view_reviews"
        assert Permission.ADMIN.value == "admin"


class TestRole:
    def test_owner_has_all_permissions(self):
        role = ROLES["owner"]
        for perm in Permission:
            assert role.has_permission(perm)

    def test_viewer_only_has_view(self):
        role = ROLES["viewer"]
        assert role.has_permission(Permission.VIEW_REVIEWS)
        assert not role.has_permission(Permission.CREATE_REVIEW)

    def test_member_can_create_review(self):
        role = ROLES["member"]
        assert role.has_permission(Permission.CREATE_REVIEW)


class TestMembership:
    def test_can_check_permission(self):
        m = Membership("user1", "org1", "member")
        assert m.can(Permission.VIEW_REVIEWS)
        assert not m.can(Permission.ADMIN)


class TestAccessControl:
    def test_add_and_check(self):
        ac = AccessControl()
        ac.add_member("org1", "alice", "member")
        assert ac.check("org1", "alice", Permission.VIEW_REVIEWS)
        assert not ac.check("org1", "alice", Permission.ADMIN)

    def test_unknown_user_denied(self):
        ac = AccessControl()
        assert not ac.check("org1", "nobody", Permission.VIEW_REVIEWS)

    def test_remove_member(self):
        ac = AccessControl()
        ac.add_member("org1", "bob", "member")
        ac.remove_member("org1", "bob")
        assert not ac.check("org1", "bob", Permission.VIEW_REVIEWS)

    def test_role_upgrade(self):
        ac = AccessControl()
        ac.add_member("org1", "alice", "viewer")
        ac.add_member("org1", "alice", "admin")
        assert ac.check("org1", "alice", Permission.ADMIN)

    def test_list_members(self):
        ac = AccessControl()
        ac.add_member("org1", "alice", "admin")
        ac.add_member("org1", "bob", "member")
        members = ac.list_members("org1")
        assert len(members) == 2
