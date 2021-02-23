#!/bin/bash

name=aqueduct_addon
version=v0.1
folder=./aqueduct

mkdir "$folder"
cp __init__.py "$folder"
cp ad_gui.py "$folder"
cp ad_ops_export.py "$folder"
cp ad_ops_filelist.py "$folder"
cp ad_ops_import.py "$folder"
cp ad_ops_tools.py "$folder"
cp ad_ops_utility.py "$folder"
cp ad_utils.py "$folder"
cp ./resources "$folder"
zip -r "${name}_${version}.zip" "$folder"
rm -r "$folder"
