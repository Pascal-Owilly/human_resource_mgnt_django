#!/bin/bash

# Stage all changes
git add .

# Commit changes with the message "update"
git commit -m "update"

# Push changes to the 'master-6' branch on the remote repository
git push origin master-6
