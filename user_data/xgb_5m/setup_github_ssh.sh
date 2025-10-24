#!/bin/bash
################################################################################
# GitHub Actions SSH Key Setup for VPS
# Run this script ON YOUR VPS
################################################################################

echo "================================================"
echo "Setting up SSH key for GitHub Actions"
echo "================================================"

# Generate SSH key for GitHub Actions
SSH_KEY_PATH="$HOME/.ssh/github_actions"

echo ""
echo "Generating SSH key pair..."
ssh-keygen -t ed25519 -f "$SSH_KEY_PATH" -N "" -C "github-actions-deploy"

echo ""
echo "Adding public key to authorized_keys..."
cat "${SSH_KEY_PATH}.pub" >> "$HOME/.ssh/authorized_keys"
chmod 600 "$HOME/.ssh/authorized_keys"

echo ""
echo "================================================"
echo "SSH Key Setup Complete!"
echo "================================================"
echo ""
echo "COPY THE PRIVATE KEY BELOW:"
echo "---BEGIN PRIVATE KEY---"
cat "$SSH_KEY_PATH"
echo "---END PRIVATE KEY---"
echo ""
echo "COPY THE PUBLIC KEY BELOW (for verification):"
echo "---BEGIN PUBLIC KEY---"
cat "${SSH_KEY_PATH}.pub"
echo "---END PUBLIC KEY---"
echo ""
echo "Next steps:"
echo "1. Copy the PRIVATE KEY above (including BEGIN/END lines)"
echo "2. Give it to Claude to update GitHub secrets"
echo "3. GitHub Actions will then be able to deploy automatically"
echo ""
