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


def create_project(project_name, base_dir):
    """Create a new project directory and initial note."""
    base_dir = os.path.expanduser(base_dir)
    project_dir = os.path.join(base_dir, project_name)

    if os.path.exists(project_dir):
        print(f"Project '{project_name}' already exists.")
        return False

    os.makedirs(project_dir)
    print(f"Created new project directory: {project_dir}")

    # Create initial README
    readme_path = os.path.join(project_dir, "README.md")
    with open(readme_path, "w") as f:
        f.write(f"# {project_name}\n\nProject created on {datetime.now().strftime('%Y-%m-%d')}")

    # Create first daily note
    create_daily_note(project_name, base_dir)
    return True


def list_projects(base_dir):
    """List all existing projects in the base directory."""
    base_dir = os.path.expanduser(base_dir)
    if not os.path.exists(base_dir):
        print(f"No projects found. Base directory '{base_dir}' does not exist.")
        return

    projects = []
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        if os.path.isdir(item_path):
            projects.append(item)

    if not projects:
        print("No projects found.")
    else:
        print("\nExisting projects:")
        for project in sorted(projects):
            print(f"- {project}")


def create_daily_note(project_name, base_dir="notes"):
    # Get today's date and yesterday's date
    today = datetime.now()
    yesterday = today - timedelta(days=1)

    today_str = today.strftime("%Y-%m-%d")
    yesterday_str = yesterday.strftime("%Y-%m-%d")

    # Expand the ~ in the path to the user's home directory
    base_dir = os.path.expanduser(base_dir)
    project_dir = os.path.join(base_dir, project_name)

    # Check if project exists
    if not os.path.exists(project_dir):
        print(f"Project '{project_name}' does not exist. Create it first using the 'new' command.")
        return False

    # Define the filenames within the project directory
    today_filename = os.path.join(project_dir, f"{today_str}.md")
    yesterday_filename = os.path.join(project_dir, f"{yesterday_str}.md")

    # Get incomplete tasks from yesterday
    carried_tasks = get_incomplete_tasks(yesterday_filename)
    carried_tasks_str = "\n".join(carried_tasks) if carried_tasks else "- No tasks carried over"

    # Get expected tasks from yesterday
    expected_tasks = get_expected_tasks(yesterday_filename)
    expected_tasks_str = "- No expected tasks" if not expected_tasks else "\n".join(expected_tasks)

    # Check if today's file already exists
    if os.path.exists(today_filename):
        print(f"File '{today_filename}' already exists.")
        return False

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
    return True


def main():
    parser = argparse.ArgumentParser(description="Manage daily notes for projects.")
    parser.add_argument("--base-dir", default="~/.notes", help="Base directory to save notes (default: '~/.notes')")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # New project command
    new_parser = subparsers.add_parser("new", help="Create a new project")
    new_parser.add_argument("project_name", help="Name of the project")

    # List projects command
    subparsers.add_parser("list", help="List existing projects")

    # Create daily note command
    daily_parser = subparsers.add_parser("daily", help="Create a daily note for a project")
    daily_parser.add_argument("project_name", help="Name of the project")

    args = parser.parse_args()

    if args.command == "new":
        create_project(args.project_name, args.base_dir)
    elif args.command == "list":
        list_projects(args.base_dir)
    elif args.command == "daily":
        create_daily_note(args.project_name, args.base_dir)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()