@echo off
SET BLENDER_DIR="C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
SET SOURCE_DIR=.\..\src\r0tools_simple_toolbox
SET OUTPUT_DIR=.\
SET REPO_DIR=.\..\..\blender-addons-repo\release

rem Build the extension
%BLENDER_DIR% -b --factory-startup --command extension build --source-dir %SOURCE_DIR% --output-dir %REPO_DIR%

rem Generate server files
%BLENDER_DIR% -b --factory-startup --command extension server-generate --repo-dir %REPO_DIR%
pause
@echo on
