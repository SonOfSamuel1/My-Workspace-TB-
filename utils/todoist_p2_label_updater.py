#!/usr/bin/env python3
"""
Script to add the P2 label to all priority 2 tasks in Todoist.
Priority 2 in Todoist API corresponds to "High" priority (p2 filter).
"""

import requests
import time
from typing import List, Dict

# Configuration
TODOIST_API_TOKEN = input("Please enter your Todoist API token: ").strip()
P2_LABEL_NAME = "P2"
P2_LABEL_ID = "2182316525"
BASE_URL = "https://api.todoist.com/rest/v2"

headers = {
    "Authorization": f"Bearer {TODOIST_API_TOKEN}",
    "Content-Type": "application/json"
}

def get_all_projects() -> List[Dict]:
    """Fetch all projects from Todoist."""
    response = requests.get(f"{BASE_URL}/projects", headers=headers)
    response.raise_for_status()
    return response.json()

def get_tasks_for_project(project_id: str) -> List[Dict]:
    """Fetch all tasks for a specific project."""
    response = requests.get(f"{BASE_URL}/tasks", headers=headers, params={"project_id": project_id})
    response.raise_for_status()
    return response.json()

def update_task_labels(task_id: str, labels: List[str]) -> bool:
    """Update a task's labels."""
    try:
        response = requests.post(
            f"{BASE_URL}/tasks/{task_id}",
            headers=headers,
            json={"labels": labels}
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"  Error updating task {task_id}: {e}")
        return False

def main():
    print("Starting P2 label update process...\n")

    # Get all projects
    print("Fetching all projects...")
    projects = get_all_projects()
    print(f"Found {len(projects)} projects\n")

    total_updated = 0
    total_p2_tasks = 0

    # Process each project
    for i, project in enumerate(projects, 1):
        project_name = project['name']
        project_id = project['id']

        print(f"[{i}/{len(projects)}] Processing project: {project_name}")

        try:
            # Get all tasks for this project
            tasks = get_tasks_for_project(project_id)

            # Filter for priority 2 tasks (API uses priority value of 2 for "High" priority)
            p2_tasks = [task for task in tasks if task.get('priority') == 2]

            if p2_tasks:
                print(f"  Found {len(p2_tasks)} priority 2 tasks")
                total_p2_tasks += len(p2_tasks)

                for task in p2_tasks:
                    task_id = task['id']
                    task_content = task['content'][:50]  # First 50 chars
                    current_labels = task.get('labels', [])

                    # Check if P2 label is already present
                    if P2_LABEL_NAME in current_labels:
                        print(f"  - '{task_content}...' already has P2 label, skipping")
                    else:
                        # Add P2 label to existing labels
                        new_labels = current_labels + [P2_LABEL_NAME]

                        if update_task_labels(task_id, new_labels):
                            print(f"  - Updated '{task_content}...' with P2 label")
                            total_updated += 1

                        # Rate limiting: be nice to the API
                        time.sleep(0.5)
            else:
                print(f"  No priority 2 tasks found")

        except Exception as e:
            print(f"  Error processing project: {e}")

        # Small delay between projects
        time.sleep(0.5)

    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Total priority 2 tasks found: {total_p2_tasks}")
    print(f"Tasks updated with P2 label: {total_updated}")
    print(f"Tasks that already had P2 label: {total_p2_tasks - total_updated}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
