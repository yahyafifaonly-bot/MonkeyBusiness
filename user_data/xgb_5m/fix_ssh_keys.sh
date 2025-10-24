#!/bin/bash
################################################################################
# Fix SSH authorized_keys on VPS
# Run this ON YOUR VPS to properly format the keys
################################################################################

echo "Fixing SSH authorized_keys formatting..."

# Backup current file
cp ~/.ssh/authorized_keys ~/.ssh/authorized_keys.backup.$(date +%s)

# Create properly formatted authorized_keys
cat > ~/.ssh/authorized_keys << 'ENDKEYS'
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC19u5ILjI9q2iA29msGOlyZGkM3EdCIPpUcH1HDQ9wVfBzf8VhU5ElBJfSJJODfFGpJ/tBQlrQxTk4/6xTssuNOXH+0tye5fCqcWZNQzGJccfKgZLVhSXKpnpgfQyBiRgBOBcc4euGzEfAUl4Qk/Mft16Z1yktqgbsgnf/IqdOGvTfJ6p8PMfhLAg3JjRiqwHA+4Zbey/PFr59LIkmwDSNAG5LLgbCS9dTijpYzuR+8TePWZNCfbKFEzhxcZRbno6Fnt4vd2wx8O9ozj8ncST9rNAj32+3eHhGA/SgdBj3yDeKdfJ/ZH690ozzY3SngXOyoqcUL1Fu/4Je3xGjc6iBjr0VaHcwj9RO5lFdD0kjYcmX0WGKjW/PvEk+2DBV6X+yccD1W7CfRCV8JYLETpI0isfrTtdE3RAIbIe3UGpgfG7DDP36cGGg3pU6IGjAGVW79Znucsc8GYZqVgRBBv2fk98Vr8DhJPWXt0TXgktaxyBZVjgB9RAbm5MOfSGVIRuG1zJcCFAyHHL9azoVNHuexHeP7gcw4jfXHsqbbWzwooG55I8g2yjNusFHhhGB+SAka4DmSuQSVPNVAAtlgdejGJq0Bv7ylXlabwckd6hcQmHA89Wq/AFImhXDjCMFiEVQAEYJicpP9Q0vOFG4/pirOG+ef8hh2j+UQhkIUNuvHQ== #hostinger-managed-key
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDkqvU4A7de8/Xa2mXqhD4zVAy/YZcjJZSaI5M3Il+/NmbSzTSfLz8bV/z4KrM4G3CneBjjfLQ/3AQg3E018woExWhymUzHI6HI33+7U+0kVJZFv4dnU8i7CKHy0OG2P38Ki06s2SPUrE3HBLG0gdAM5Z4wJgLc99kTqC2s1GNwl8o+yMbewAS246ad7Mji3JTo83Tb3Is8DMyIKdaWAnnIpl6keu5I/+CxHQeFDXmhXWYfHw5QHj/flknvEbj+TIgT5JdQPmjxoc+0c3wArs1nBOzspoY5jXgNnLOADFiyHeCgHZkLckdRlwoMyJrARJJnY8jVf9Zcvp5BecWihl+vD53jCE5aepyO9kxB4QZuDmVEmWQhiSKTbJFl3Lh7yXc4RBeeDRzjuNhtWvmlFNB0+6pNxjj1/bq7dt8/KmKlSpcbbOVb02JOF1SCoPDfjWOvBIh0+NUf0xvCOM0BEZ2lcB390rpySmLmx/pFLouvCsdq2EJ+y4ok6Dzbo5rSg9LRGIPHMsOfynAnmPME3AKUySgTmnaxXmYC6A8s6ClCYFvgOByieXUhAboHJcdK7Vjh03UhnrVal/VPwyjcIaXgecFlTPbFolMMU/qoQAFwynfhK+HiS+XPdV3A7XTYpLfFbGN//E0U/pIUv2FHMf5/llqt5LVUC0Uome9z5coxJQ== #hostinger-managed-key
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExw0V0nwJQhEqvM9HwZACMeIP0qXfgSFs5gUiayymw0 github-actions-deploy
ENDKEYS

# Fix permissions
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys

echo ""
echo "✓ Fixed! authorized_keys now has $(wc -l < ~/.ssh/authorized_keys) keys"
echo ""
echo "Keys in file:"
nl ~/.ssh/authorized_keys | head -n 20
echo ""
echo "GitHub Actions key verified:"
grep -n "github-actions" ~/.ssh/authorized_keys
