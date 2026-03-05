#!/bin/bash

BLENDER_DIR="/usr/bin/blender" # TODO: Verify and change to proper path
SOURCE_DIR="../src/r0tools_simple_toolbox"
OUTPUT_DIR="./"
REPO_DIR="../../blender-addons-repo/release"

# Build the extension
"$BLENDER_DIR" -b --factory-startup --command extension build --source-dir "$SOURCE_DIR" --output-dir "$REPO_DIR"

echo -e "\nPress ENTER to continue generating server files. This is your chance to rename the file(s) if needed."
read -r

# Generate server files
"$BLENDER_DIR" -b --factory-startup --command extension server-generate --repo-dir "$REPO_DIR"
