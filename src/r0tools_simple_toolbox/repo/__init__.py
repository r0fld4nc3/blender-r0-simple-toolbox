REPOSITORY = "https://www.github.com/r0fld4nc3/blender-r0-simple-toolbox"
ISSUES_PAGE = REPOSITORY + "/issues"
ISSUES_BUG_ADD = ISSUES_PAGE + "/new?template=bug_report.md"
ISSUES_FEATURE_ADD = ISSUES_PAGE + "/new?template=feature_request.md"
RELEASES_PAGE = REPOSITORY + "/releases"

from .operators import (
    SimpleToolbox_OT_OpenCreateIssueBug,
    SimpleToolbox_OT_OpenCreateIssueFeature,
    SimpleToolbox_OT_OpenReleasesPage,
    SimpleToolbox_OT_OpenRepositoryIssuePage,
    SimpleToolbox_OT_OpenRepositoryUrl,
)
from .ui import draw_repo_layout
