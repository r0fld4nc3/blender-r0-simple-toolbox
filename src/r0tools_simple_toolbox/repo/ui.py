import bpy
from bpy.props import BoolProperty  # type: ignore


def draw_repo_layout(layout, context):
    from ..utils import get_addon_prefs

    wm = context.window_manager

    addon_prefs = get_addon_prefs()

    main_box = layout.box()
    main_box.prop(
        wm,
        "show_repo_panel_ui",
        icon="TRIA_DOWN" if wm.show_repo_panel_ui else "TRIA_RIGHT",
        emboss=False,
    )
    if wm.show_repo_panel_ui:
        header_row = main_box.row()
        header_row.label(text="SimpleToolbox GitHub", icon="URL")

        repo_box = main_box.box()

        row = repo_box.row()
        split = row.split(factor=0.5)
        # Homepage and Releases
        split.operator("r0tools.open_repo_homepage", icon="URL")
        split.operator("r0tools.open_repo_releases_page", icon="URL")
        # Check Update Button
        row = repo_box.row()
        row.operator("r0tools.check_for_update", icon="FILE_REFRESH")
        # Check Update on Startup
        row = repo_box.row()
        row.prop(addon_prefs, "check_update_startup", text="Check Update on Startup")

        issues_box = main_box.box()
        row = issues_box.row()
        # Report Bug & Feature
        split = row.split(factor=0.5)
        split.operator("r0tools.open_repo_issue_bug_report", icon="URL")
        split.operator("r0tools.open_repo_issue_feature_request", icon="URL")
        # Open Issues Page
        row = issues_box.row()
        row.operator("r0tools.open_repo_issue_page", icon="URL")


def register():
    bpy.types.WindowManager.show_repo_panel_ui = BoolProperty(  # type: ignore
        name="GitHub",
        description="Show or hide the GitHub repository UI drawer.",
        default=False,
        options={"SKIP_SAVE"},
    )


def unregister():
    del bpy.types.WindowManager.show_repo_panel_ui
