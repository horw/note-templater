import os
from datetime import datetime, timedelta, date
import argparse
import calendar
import math

# Previous template definition remains the same
TEMPLATE = """# Daily Note - {date} - {project_name}

## Goals for Today
- [ ] Goal 1
- [ ] Goal 2
- [ ] Goal 3

## Tasks
{carried_tasks}

## Notes
- Note 1
- Note 2

## Expected for Tomorrow
{expected_tasks}

## Reflections
- What went well today?
- What could be improved?
"""

def get_template_tasks():
    output = []
    for i in range(3):
        output.append(" -  Task {}".format(i))
    return '\n'.join(output)

# Previous functions remain the same (get_incomplete_tasks, get_expected_tasks)
def get_incomplete_tasks(filename):
    """Extract incomplete tasks from a previous note."""
    if not os.path.exists(filename):
        return []

    with open(filename, 'r') as file:
        content = file.read()

    tasks = []
    in_tasks_section = False

    for line in content.split('\n'):
        if '## Tasks' in line:
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


def count_completed_tasks(filename):
    """Count completed tasks in a note file."""
    if not os.path.exists(filename):
        return 0

    with open(filename, 'r') as file:
        content = file.read()

    completed_tasks = content.count('- [x]')
    return completed_tasks


def generate_contribution_graph(project_name, base_dir, months=12):
    """Generate a GitHub-like contribution graph for the project."""
    base_dir = os.path.expanduser(base_dir)
    project_dir = os.path.join(base_dir, project_name)

    if not os.path.exists(project_dir):
        print(f"Project '{project_name}' does not exist.")
        return

    # Calculate date range
    end_date = date.today()
    start_date = end_date - timedelta(days=months * 30)  # Approximate months

    # Collect data
    contribution_data = {}
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        filename = os.path.join(project_dir, f"{date_str}.md")

        if os.path.exists(filename):
            completed_tasks = count_completed_tasks(filename)
            # Calculate activity level (0-4)
            if completed_tasks == 0:
                level = 1  # Light green for just creating a note
            else:
                level = min(4, 1 + math.floor(completed_tasks / 3))  # More tasks = darker green
        else:
            level = 0  # No activity

        contribution_data[date_str] = level
        current_date += timedelta(days=1)

    # Generate ASCII visualization
    print(f"\nContribution graph for {project_name} (last {months} months):")
    print("Less " + "─" * 20 + " More")
    print("█ = High activity  ▓ = Medium  ▒ = Low  ░ = Very Low  · = None\n")

    # Generate month labels
    months_label = ""
    current_date = start_date
    while current_date <= end_date:
        if current_date.day == 1:
            months_label += f"{current_date.strftime('%b')}   "
        current_date += timedelta(days=1)
    print(months_label)

    # Generate the graph
    for day_of_week in range(7):
        row = ""
        current_date = start_date + timedelta(days=(7 - start_date.weekday() + day_of_week) % 7)
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            level = contribution_data.get(date_str, 0)

            # Use different characters for different activity levels
            if level == 0:
                row += "·"
            elif level == 1:
                row += "░"
            elif level == 2:
                row += "▒"
            elif level == 3:
                row += "▓"
            else:
                row += "█"

            row += " "
            current_date += timedelta(days=7)
        print(row)
    print()


def find_last_note(project_dir):
    """Find the most recent note file in the project directory."""
    if not os.path.exists(project_dir):
        return None

    # Get all .md files except README.md
    note_files = [f for f in os.listdir(project_dir)
                  if f.endswith('.md') and f != 'README.md']

    if not note_files:
        return None

    # Sort files by date (files are named YYYY-MM-DD.md)
    note_files.sort(reverse=True)

    # Return the most recent file
    return os.path.join(project_dir, note_files[0])


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
            # Generate contribution graph for each project
            generate_contribution_graph(project, base_dir)


def create_daily_note(project_name, base_dir="notes"):
    # Get today's date
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")

    # Expand the ~ in the path to the user's home directory
    base_dir = os.path.expanduser(base_dir)
    project_dir = os.path.join(base_dir, project_name)

    # Check if project exists
    if not os.path.exists(project_dir):
        print(f"Project '{project_name}' does not exist. Create it first using the 'new' command.")
        return False

    # Define today's filename
    today_filename = os.path.join(project_dir, f"{today_str}.md")

    # Find the last note
    last_note = find_last_note(project_dir)

    # Get incomplete tasks from last note
    carried_tasks = []
    expected_tasks = []
    if last_note:
        carried_tasks = get_incomplete_tasks(last_note)
        carried_tasks.extend(get_expected_tasks(last_note))
        last_note_date = os.path.basename(last_note).replace('.md', '')
        print(f"Processing tasks from last note: {last_note_date}")

    carried_tasks_str = "\n".join(carried_tasks) if carried_tasks else get_template_tasks()
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
        print(f"Carried over {len(carried_tasks)} incomplete tasks from last note.")
    return True


def main():
    parser = argparse.ArgumentParser(description="Manage daily notes for projects.")
    parser.add_argument("--base-dir", default="~/.notes", help="Base directory to save notes (default: '~/.notes')")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # New project command
    new_parser = subparsers.add_parser("new", help="Create a new project")
    new_parser.add_argument("project_name", help="Name of the project")

    # List projects command
    list_parser = subparsers.add_parser("list", help="List existing projects")
    list_parser.add_argument("--months", type=int, default=12, help="Number of months to show in contribution graph")

    # Create daily note command
    daily_parser = subparsers.add_parser("daily", help="Create a daily note for a project")
    daily_parser.add_argument("project_name", help="Name of the project")

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show contribution graph for a specific project")
    stats_parser.add_argument("project_name", help="Name of the project")
    stats_parser.add_argument("--months", type=int, default=12, help="Number of months to show in contribution graph")

    args = parser.parse_args()

    if args.command == "new":
        create_project(args.project_name, args.base_dir)
    elif args.command == "list":
        list_projects(args.base_dir)
    elif args.command == "daily":
        create_daily_note(args.project_name, args.base_dir)
    elif args.command == "stats":
        generate_contribution_graph(args.project_name, args.base_dir, args.months)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()