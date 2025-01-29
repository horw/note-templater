import os
from datetime import datetime, timedelta
import argparse

# Define the template for the daily note
TEMPLATE = """# Daily Note - {date} - {project_name}

## Carried Over Tasks
{carried_tasks}

## Goals for Today
- [ ] Goal 1
- [ ] Goal 2
- [ ] Goal 3

## Tasks
- [ ] Task 1
- [ ] Task 2
- [ ] Task 3

## Notes
- Note 1
- Note 2

## Expected for Tomorrow
{expected_tasks}

## Reflections
- What went well today?
- What could be improved?
"""


def get_incomplete_tasks(filename):
    """Extract incomplete tasks from a previous note."""
    if not os.path.exists(filename):
        return []

    with open(filename, 'r') as file:
        content = file.read()

    tasks = []
    in_tasks_section = False

    for line in content.split('\n'):
        if '## Tasks' in line or '## Carried Over Tasks' in line:
            in_tasks_section = True
        elif line.startswith('##'):
            in_tasks_section = False
        elif in_tasks_section and line.startswith('- [ ]'):
            tasks.append(line)

    return tasks


def get_expected_tasks(filename):
    """Extract expected tasks for tomorrow from the current note."""
    if not os.path.exists(filename):
        return []

    with open(filename, 'r') as file:
        content = file.read()

    tasks = []
    in_expected_section = False

    for line in content.split('\n'):
        if '## Expected for Tomorrow' in line:
            in_expected_section = True
        elif line.startswith('##'):
            in_expected_section = False
        elif in_expected_section and line.startswith('-'):
            tasks.append(line)

    return tasks


def create_daily_note(project_name, base_dir="notes"):
    # Get today's date and yesterday's date
    today = datetime.now()
    yesterday = today - timedelta(days=1)

    today_str = today.strftime("%Y-%m-%d")
    yesterday_str = yesterday.strftime("%Y-%m-%d")

    # Expand the ~ in the path to the user's home directory
    base_dir = os.path.expanduser(base_dir)

    # Create the base directory if it doesn't exist
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
        print(f"Created base directory: {base_dir}")

    # Define the filenames
    today_filename = os.path.join(base_dir, f"{today_str}_{project_name}.md")
    yesterday_filename = os.path.join(base_dir, f"{yesterday_str}_{project_name}.md")

    # Get incomplete tasks from yesterday
    carried_tasks = get_incomplete_tasks(yesterday_filename)
    carried_tasks_str = "\n".join(carried_tasks) if carried_tasks else "- No tasks carried over"

    # Get expected tasks from yesterday
    expected_tasks = get_expected_tasks(yesterday_filename)
    expected_tasks_str = "- No expected tasks" if not expected_tasks else ""

    # Check if today's file already exists
    if os.path.exists(today_filename):
        print(f"File '{today_filename}' already exists.")
    else:
        # Create the file and write the template
        with open(today_filename, "w") as file:
            file.write(TEMPLATE.format(
                date=today_str,
                project_name=project_name,
                carried_tasks=carried_tasks_str,
                expected_tasks=expected_tasks_str
            ))
        print(f"Created file '{today_filename}' with the daily note template.")
        if carried_tasks:
            print(f"Carried over {len(carried_tasks)} incomplete tasks from yesterday.")


def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Create a daily note for a project.")
    parser.add_argument("project_name", help="Name of the project")
    parser.add_argument("--base-dir", default="~/.notes", help="Base directory to save notes (default: '~/.notes')")
    args = parser.parse_args()

    # Create the daily note
    create_daily_note(args.project_name, args.base_dir)


if __name__ == "__main__":
    main()