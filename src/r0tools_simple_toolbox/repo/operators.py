import bpy

from ..defines import DEBUG, INTERNAL_NAME
from . import ISSUES_BUG_ADD, ISSUES_FEATURE_ADD, ISSUES_PAGE, RELEASES_PAGE, REPOSITORY

_mod = "REPO.OPERATORS"


def open_url(url):
    print(f"Open url: {url}")
    bpy.ops.wm.url_open(url=url)


class SimpleToolbox_OT_OpenRepositoryUrl(bpy.types.Operator):
    bl_label = "Homepage"
    bl_idname = "r0tools.open_repo_homepage"
    bl_description = "Open the Addon's Homepage on GitHub"
    bl_options = {"REGISTER"}

    def execute(self, context):
        open_url(REPOSITORY)
        return {"FINISHED"}


class SimpleToolbox_OT_OpenRepositoryIssuePage(bpy.types.Operator):
    bl_label = "Issues"
    bl_idname = "r0tools.open_repo_issue_page"
    bl_description = "Open the Issues page, where current features, bugs and discussion is held"
    bl_options = {"REGISTER"}

    def execute(self, context):
        open_url(ISSUES_PAGE)
        return {"FINISHED"}


class SimpleToolbox_OT_OpenCreateIssueBug(bpy.types.Operator):
    bl_label = "Report a Bug"
    bl_idname = "r0tools.open_repo_issue_bug_report"
    bl_description = "Something not working? Potentially found a bug? Come right on over and let us know in our Issues page, where we track all the bugs, features and discussions surrounding them.\n\nTip: Make sure you browse through existing issues to check if your issue isn't a duplicate"
    bl_options = {"REGISTER"}

    def execute(self, context):
        open_url(ISSUES_BUG_ADD)
        return {"FINISHED"}


class SimpleToolbox_OT_OpenCreateIssueFeature(bpy.types.Operator):
    bl_label = "Request a Feature"
    bl_idname = "r0tools.open_repo_issue_feature_request"
    bl_description = "Have something you'd like added, or changed? Know how to improve something existing, or want to suggest something to empower your workflow? Come on over to our Issues page, where we track all the bugs, features and discussions surrounding them.\n\nTip: Make sure you browse through existing issues to check if your issue isn't a duplicate"
    bl_options = {"REGISTER"}

    def execute(self, context):
        open_url(ISSUES_FEATURE_ADD)
        return {"FINISHED"}


class SimpleToolbox_OT_OpenReleasesPage(bpy.types.Operator):
    bl_label = "Releases"
    bl_idname = "r0tools.open_repo_releases_page"
    bl_description = "Looking for a specific release? Want to install it offline without relying on online extensions? This is the page to find them, but be warned: they are older versions and may not contain all the brand-spanking new and improved fixes and functionality"
    bl_options = {"REGISTER"}

    def execute(self, context):
        open_url(RELEASES_PAGE)
        return {"FINISHED"}


class SimpleToolbox_OT_TakeMeToUpdate(bpy.types.Operator):
    bl_label = "Check Update"
    bl_idname = "r0tools.take_me_to_update"
    bl_description = "Open relevant page to update the addon"
    bl_options = {"REGISTER", "INTERNAL"}

    def execute(self, context):
        split = INTERNAL_NAME.split(".")

        if "bl_ext" in split:
            # Bring up the User Preferences window and pre-search the addon name
            bpy.ops.screen.userpref_show()

            bpy.context.preferences.active_section = "EXTENSIONS"

            bpy.data.window_managers["WinMan"].extension_search = "r0tools"
        else:
            bpy.ops.r0tools.open_repo_releases_page()

        return {"FINISHED"}


class SimpleToolbox_OT_CheckUpdate(bpy.types.Operator):
    bl_label = "Check Update"
    bl_idname = "r0tools.check_for_update"
    bl_description = "Check for an update to the addon"
    bl_options = {"REGISTER"}

    def execute(self, context):
        from ..ext_update import trigger_thread_update_check, trigger_update_check

        # trigger_update_check()
        trigger_thread_update_check()

        return {"FINISHED"}


# -------------------------------------------------------------------
#   Register & Unregister
# -------------------------------------------------------------------

classes = [
    SimpleToolbox_OT_OpenRepositoryUrl,
    SimpleToolbox_OT_OpenRepositoryIssuePage,
    SimpleToolbox_OT_OpenCreateIssueBug,
    SimpleToolbox_OT_OpenCreateIssueFeature,
    SimpleToolbox_OT_OpenReleasesPage,
    SimpleToolbox_OT_TakeMeToUpdate,
    SimpleToolbox_OT_CheckUpdate,
]


def register():
    for cls in classes:
        if DEBUG:
            print(f"[INFO] [{_mod}] Register {cls.__name__}")
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        if DEBUG:
            print(f"[INFO] [{_mod}] Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)
