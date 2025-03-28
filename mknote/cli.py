import json
import os
from datetime import datetime, timedelta, date
import argparse
import math
import requests
import pyperclip
import subprocess
import tempfile
import csv
import time
import threading
import pyautogui  # For auto-pasting functionality

CONFIG_FILE = os.path.expanduser("~/.noter-config")


def load_config():
    """Load configuration from file."""
    default_config = {
        "base_dir": os.path.expanduser("~/.notes"),
        "gemini_api_key": "",
        "editor": "vim",
        "template_path": ""
    }
    
    if not os.path.exists(CONFIG_FILE):
        # Create the initial config file with default values
        save_config(default_config)
        return default_config

    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            
            # Ensure all expected keys exist in the config
            # This handles the case where the config file exists but is missing some keys
            for key, value in default_config.items():
                if key not in config:
                    config[key] = value
                    
            return config
    except json.JSONDecodeError:
        # If the config file is corrupted, reset it with defaults
        save_config(default_config)
        return default_config


def save_config(config):
    """Save configuration to file."""
    with open(CONFIG_FILE, 'w+') as f:
        json.dump(config, f, indent=2)


def set_base_dir(base_dir):
    """Set and save base directory configuration."""
    base_dir = os.path.expanduser(base_dir)
    config = load_config()
    config["base_dir"] = base_dir
    save_config(config)

    return base_dir

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


def get_important_items(filename):
    """Extract important items from a note file.
    [!] - open items
    [!!] - closed items
    """
    if not os.path.exists(filename):
        return []

    items = []
    current_section = None
    current_text = []

    with open(filename, 'r', encoding='utf-8') as file:
        for line in file:

            if line.startswith('##'):
                current_section = line[2:].strip()
                continue

            if current_text:  # If we're in an item, collect additional lines
                current_text.append(line)

            if '[!]' in line:
                current_text = [' ', line]

            if '[!!]' in line:
                if current_text:  # Save previous item if exists
                    items.append({
                        'item': ''.join(current_text).split('[!]')[1].split('[!!]')[0],
                        'section': current_section,
                        'date': os.path.basename(filename).replace('.md', ''),
                    })
                current_text = []


    return items


def display_important_items(project_name, base_dir):
    """Display all important items from a project's notes."""
    base_dir = os.path.expanduser(base_dir)
    project_dir = os.path.join(base_dir, project_name)

    if not os.path.exists(project_dir):
        print(f"Project '{project_name}' does not exist.")
        return

    all_important_items = []
    for filename in os.listdir(project_dir):
        if filename.endswith('.md') and filename != 'README.md':
            file_path = os.path.join(project_dir, filename)
            items = get_important_items(file_path)
            all_important_items.extend(items)

    if not all_important_items:
        print(f"No important items found in project '{project_name}'")
        return

    print(f"\nImportant Items for project '{project_name}':")
    print("-" * 50)

    # Sort items by date
    all_important_items.sort(key=lambda x: x['date'], reverse=True)

    current_date = None
    for item in all_important_items:
        if current_date != item['date']:
            current_date = item['date']
            print(f"\n***** {current_date} *****\n")
        print(f"[{item['section']}] \n\n {item['item']}")

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


def open_vscode(base_dir):
    """Open VSCode in the specified base directory.

    Args:
        base_dir (str): Base directory path where notes are stored
    """
    import subprocess

    base_dir = os.path.expanduser(base_dir)
    subprocess.Popen(['code', base_dir])


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


def log_grammar_check(request_text, corrected_text):
    """
    Log the grammar check request and result to a log file.
    
    Args:
        request_text (str): The original text that was checked
        corrected_text (str): The corrected text returned by the API
    """
    config = load_config()
    base_dir = os.path.expanduser(config["base_dir"])
    logs_dir = os.path.join(base_dir, "_logs")
    
    # Create logs directory if it doesn't exist
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir, exist_ok=True)
    
    # Create a log file path with current date
    now = datetime.now()
    log_file = os.path.join(logs_dir, f"grammar_checks_{now.strftime('%Y-%m')}.csv")
    
    # Check if file exists to determine if we need to write header
    file_exists = os.path.isfile(log_file)
    
    # Get timestamp
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # Write to CSV file
    with open(log_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write header if file is new
        if not file_exists:
            writer.writerow(["Timestamp", "Original Text", "Corrected Text"])
        
        # Write the data row
        writer.writerow([timestamp, request_text, corrected_text])
        
    print(f"Logged grammar check to {log_file}")
    
    # Return the path to the log file
    return log_file


def view_grammar_logs(month=None, limit=10, entry_id=None, export=False):
    """
    View grammar check logs for a specific month.
    
    Args:
        month (str): Month in YYYY-MM format. If None, use current month.
        limit (int): Maximum number of entries to display
        entry_id (int): If specified, show only this entry in detail
        export (bool): If True, export the entry to a file
    """
    config = load_config()
    base_dir = os.path.expanduser(config["base_dir"])
    logs_dir = os.path.join(base_dir, "_logs")
    
    # Create logs directory if it doesn't exist
    if not os.path.exists(logs_dir):
        print("No logs found.")
        return
    
    # Default to current month if not specified
    if month is None:
        now = datetime.now()
        month = now.strftime('%Y-%m')
    
    # Construct log file path
    log_file = os.path.join(logs_dir, f"grammar_checks_{month}.csv")
    
    if not os.path.exists(log_file):
        print(f"No logs found for {month}.")
        return
    
    # Read the CSV file
    entries = []
    try:
        with open(log_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)  # Skip header row
            
            for row in reader:
                if len(row) >= 3:  # Ensure the row has all necessary columns
                    timestamp, original, corrected = row[0], row[1], row[2]
                    entries.append((timestamp, original, corrected))
    except Exception as e:
        print(f"Error reading log file: {e}")
        return
    
    if not entries:
        print(f"No entries found in {month} log file.")
        return
    
    # Sort entries by timestamp (most recent first)
    entries.sort(reverse=True)
    
    # If entry_id is specified, show only that entry in detail
    if entry_id is not None:
        try:
            entry_idx = int(entry_id) - 1
            if entry_idx < 0 or entry_idx >= len(entries):
                print(f"Error: Entry {entry_id} not found. Valid range is 1-{len(entries)}.")
                return
                
            timestamp, original, corrected = entries[entry_idx]
            
            print(f"\nDetailed Grammar Check Log Entry [{entry_id}]")
            print(f"Timestamp: {timestamp}")
            print("-" * 50)
            
            print("\nORIGINAL TEXT:")
            print("-" * 15)
            print(original)
            
            print("\nCORRECTED TEXT:")
            print("-" * 15)
            print(corrected)
            
            # If export is requested, save to a file
            if export:
                export_dir = os.path.join(logs_dir, "exports")
                os.makedirs(export_dir, exist_ok=True)
                
                # Generate a filename based on timestamp
                safe_timestamp = timestamp.replace(":", "-").replace(" ", "_")
                export_file = os.path.join(export_dir, f"grammar_check_{safe_timestamp}.md")
                
                with open(export_file, 'w', encoding='utf-8') as f:
                    f.write(f"# Grammar Check - {timestamp}\n\n")
                    f.write("## Original Text\n\n")
                    f.write(original)
                    f.write("\n\n## Corrected Text\n\n")
                    f.write(corrected)
                
                print(f"\nExported to: {export_file}")
                
                # Ask if user wants to copy corrected text to clipboard
                copy_to_clipboard = input("\nCopy corrected text to clipboard? (y/n): ").lower().strip()
                if copy_to_clipboard == 'y' or copy_to_clipboard == 'yes':
                    pyperclip.copy(corrected)
                    print("Corrected text copied to clipboard.")
            
            return
        except ValueError:
            print("Error: Entry ID must be a number.")
            return
    
    # Display entries (limited by the limit parameter)
    print(f"\nGrammar Check Logs for {month}")
    print("-" * 50)
    
    # Limit the number of entries
    displayed_entries = entries[:limit]
    
    for i, (timestamp, original, corrected) in enumerate(displayed_entries, 1):
        print(f"\n[{i}] {timestamp}")
        
        # Truncate and display original text
        orig_preview = original[:80] + "..." if len(original) > 80 else original
        print(f"\nOriginal: {orig_preview}")
        
        # Truncate and display corrected text
        if corrected.startswith("ERROR") or corrected.startswith("API_ERROR") or corrected in ["NO_CORRECTION_RECEIVED", "UNEXPECTED_API_RESPONSE"]:
            print(f"Result: {corrected}")
        else:
            corr_preview = corrected[:80] + "..." if len(corrected) > 80 else corrected
            print(f"Corrected: {corr_preview}")
        
        print("-" * 30)
    
    if len(entries) > limit:
        print(f"\nShowing {limit} of {len(entries)} entries. Use --limit to show more.")
    
    print(f"\nTo view full details of an entry, use: mknote grammar-logs --month {month} --entry <entry_number>")
    print(f"To export an entry to a file, add --export to the command above")
    
    # Show available log files
    print("\nAvailable monthly logs:")
    log_files = [f.replace("grammar_checks_", "").replace(".csv", "") 
                for f in os.listdir(logs_dir) 
                if f.startswith("grammar_checks_") and f.endswith(".csv")]
    log_files.sort(reverse=True)
    print(", ".join(log_files))

def command_line(text):
    """Check and correct grammar for text in the clipboard using Gemini API."""
    # Load configuration to get API key
    config = load_config()
    api_key = config.get("gemini_api_key")

    if not api_key or api_key == "YOUR_API_KEY_HERE" or api_key == "":
        print("Gemini API key not set. Let's configure it now.")
        print("You'll need a Gemini API key from https://ai.google.dev/")

        # Ask for the API key
        new_key = input("Enter your Gemini API key: ").strip()
        if not new_key:
            print("No API key provided. Exiting.")
            return

        # Save the new API key
        config["gemini_api_key"] = new_key
        save_config(config)
        api_key = new_key
        print("API key saved successfully!")

    # Get text from clipboard or use provided text
    if text is None:
        try:
            text = pyperclip.paste()
            if not text:
                print("No text found in clipboard.")
                return
            print("Using text from clipboard.")
        except Exception as e:
            print(f"Error accessing clipboard: {e}")
            return

    # Show a preview of the text to be checked
    preview = text[:60] + "..." if len(text) > 60 else text
    print(f"Text to check ({len(text)} characters):")
    print(f"\"{preview}\"")

    print("\nChecking grammar...", end="", flush=True)

    # Prepare prompt for Gemini API
    prompt = f"""Please I working in terminal and want you give me  advice for follow command
    Return ONLY the corrected text without any explanations or comments:

    {text}"""

    # Call Gemini API
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    try:
        # Show a simple progress indicator
        import threading
        import time

        stop_progress = False

        def progress_indicator():
            progress_chars = ["-", "\\", "|", "/"]
            i = 0
            while not stop_progress:
                print(f"\rChecking grammar... {progress_chars[i % 4]}", end="", flush=True)
                i += 1
                time.sleep(0.2)

        # Start progress indicator thread
        progress_thread = threading.Thread(target=progress_indicator)
        progress_thread.daemon = True
        progress_thread.start()

        # Make the API request
        response = requests.post(url, headers=headers, json=data)

        # Stop the progress indicator
        stop_progress = True
        progress_thread.join(timeout=0.5)  # Give the thread time to stop
        print("\rChecking grammar... Done!       ")  # Clear the progress indicator

        response.raise_for_status()

        # Parse response
        result = response.json()

        if "candidates" in result and result["candidates"]:
            corrected_text = ""
            for content in result["candidates"]:
                for part in content['content'].get("parts", []):
                    if "text" in part:
                        corrected_text += part["text"]

            if corrected_text:
                # Print a comparison of the text before and after correction
                print("\nOriginal text:")
                print(f"{text[:100]}{'...' if len(text) > 100 else ''}")

                print("\nCorrected text:")
                print(f"{corrected_text[:100]}{'...' if len(corrected_text) > 100 else ''}")

                # Copy the corrected text to clipboard
                pyperclip.copy(corrected_text)
                print("Corrected text copied to clipboard.")

                # Auto-paste the corrected text if requested
                if True:
                    try:
                        # Give a short delay to ensure the clipboard has been updated
                        time.sleep(0.5)
                        # Perform the paste operation using Ctrl+V
                        pyautogui.hotkey('ctrl', 'v')
                        print("Auto-pasted corrected text.")
                    except Exception as e:
                        print(f"Auto-paste failed: {e}")

                return corrected_text
            else:
                print("No corrected text received from API.")
                # Log the failed attempt
                log_grammar_check(text, "NO_CORRECTION_RECEIVED")
        else:
            print("Unexpected API response format.")
            # Log the failed attempt
            log_grammar_check(text, "UNEXPECTED_API_RESPONSE")

    except requests.exceptions.RequestException as e:
        print(f"\nAPI request error: {e}")
        # Log the error
        log_grammar_check(text, f"API_ERROR: {str(e)}")
    except Exception as e:
        print(f"\nError processing response: {e}")
        # Log the error
        log_grammar_check(text, f"ERROR: {str(e)}")


def check_grammar(text=None, auto_paste=True):
    """Check and correct grammar for text in the clipboard using Gemini API."""
    # Load configuration to get API key
    config = load_config()
    api_key = config.get("gemini_api_key")
    
    if not api_key or api_key == "YOUR_API_KEY_HERE" or api_key == "":
        print("Gemini API key not set. Let's configure it now.")
        print("You'll need a Gemini API key from https://ai.google.dev/")
        
        # Ask for the API key
        new_key = input("Enter your Gemini API key: ").strip()
        if not new_key:
            print("No API key provided. Exiting.")
            return
            
        # Save the new API key
        config["gemini_api_key"] = new_key
        save_config(config)
        api_key = new_key
        print("API key saved successfully!")
    
    # Get text from clipboard or use provided text
    if text is None:
        try:
            text = pyperclip.paste()
            if not text:
                print("No text found in clipboard.")
                return
            print("Using text from clipboard.")
        except Exception as e:
            print(f"Error accessing clipboard: {e}")
            return
    
    # Show a preview of the text to be checked
    preview = text[:60] + "..." if len(text) > 60 else text
    print(f"Text to check ({len(text)} characters):")
    print(f"\"{preview}\"")
    
    print("\nChecking grammar...", end="", flush=True)
    
    # Prepare prompt for Gemini API
    prompt = f"""Please check and correct the grammar in the following text. 
Return ONLY the corrected text without any explanations or comments:

{text}"""
    
    # Call Gemini API
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        # Show a simple progress indicator
        import threading
        import time
        
        stop_progress = False
        
        def progress_indicator():
            progress_chars = ["-", "\\", "|", "/"]
            i = 0
            while not stop_progress:
                print(f"\rChecking grammar... {progress_chars[i % 4]}", end="", flush=True)
                i += 1
                time.sleep(0.2)
        
        # Start progress indicator thread
        progress_thread = threading.Thread(target=progress_indicator)
        progress_thread.daemon = True
        progress_thread.start()
        
        # Make the API request
        response = requests.post(url, headers=headers, json=data)
        
        # Stop the progress indicator
        stop_progress = True
        progress_thread.join(timeout=0.5)  # Give the thread time to stop
        print("\rChecking grammar... Done!       ")  # Clear the progress indicator
        
        response.raise_for_status()
        
        # Parse response
        result = response.json()

        if "candidates" in result and result["candidates"]:
            corrected_text = ""
            for content in result["candidates"]:
                for part in content['content'].get("parts", []):
                    if "text" in part:
                        corrected_text += part["text"]
            
            if corrected_text:
                # Print a comparison of the text before and after correction
                print("\nOriginal text:")
                print(f"{text[:100]}{'...' if len(text) > 100 else ''}")
                
                print("\nCorrected text:")
                print(f"{corrected_text[:100]}{'...' if len(corrected_text) > 100 else ''}")
                
                # Copy the corrected text to clipboard
                pyperclip.copy(corrected_text)
                print("Corrected text copied to clipboard.")
                
                # Auto-paste the corrected text if requested
                if auto_paste:
                    try:
                        # Give a short delay to ensure the clipboard has been updated
                        time.sleep(0.5)
                        # Perform the paste operation using Ctrl+V
                        pyautogui.hotkey('ctrl', 'v')
                        print("Auto-pasted corrected text.")
                    except Exception as e:
                        print(f"Auto-paste failed: {e}")
                
                # Log the grammar check
                log_file = log_grammar_check(text, corrected_text)

                # Notify user that grammar check is complete
                try:
                    # Create completion notification with HTML styling
                    subprocess.Popen([
                        "notify-send",
                        "Text has been checked and updated in clipboard."
                    ])
                    # Also print to console for record keeping
                    print("\n✅ Grammar check completed and clipboard updated.")
                except Exception as e:
                    # If notification fails, at least print to console
                    print(f"\n✅ Grammar check completed, but couldn't show notification: {e}")
                
                return corrected_text
            else:
                print("No corrected text received from API.")
                # Log the failed attempt
                log_grammar_check(text, "NO_CORRECTION_RECEIVED")
        else:
            print("Unexpected API response format.")
            # Log the failed attempt
            log_grammar_check(text, "UNEXPECTED_API_RESPONSE")
            
    except requests.exceptions.RequestException as e:
        print(f"\nAPI request error: {e}")
        # Log the error
        log_grammar_check(text, f"API_ERROR: {str(e)}")
    except Exception as e:
        print(f"\nError processing response: {e}")
        # Log the error
        log_grammar_check(text, f"ERROR: {str(e)}")


def edit_config():
    """Open the config file in Vim for interactive editing."""
    config = load_config()
    
    # Instructions for the user
    instructions = """
// Noter Configuration File
// Edit the values below and save the file to update your configuration.
// DO NOT change the structure of the JSON or remove any keys.
// Instructions:
//   - base_dir: Directory where your notes will be stored
//   - gemini_api_key: Your Gemini API key for grammar checking
//   - editor: Text editor to use (vim, nano, etc.)
//   - template_path: Custom template for daily notes (leave empty to use default)
//
// After editing, save and close the editor to apply changes.
// Press CTRL+C to cancel without saving.
"""
    
    # Create a template string for the config file
    config_template = {
        "base_dir": config.get("base_dir", os.path.expanduser("~/.notes")),
        "gemini_api_key": config.get("gemini_api_key", "YOUR_API_KEY_HERE"),
        "editor": config.get("editor", "vim"),
        "template_path": config.get("template_path", ""),
        # Add any other configuration options here
    }
    
    # Create a temporary file with the current config
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w+", delete=False) as temp:
        # Write instructions first (as a comment)
        temp.write(instructions)
        # Write the actual JSON content
        json.dump(config_template, temp, indent=4)
        temp_path = temp.name
    
    try:
        # Open the temporary file in Vim
        editor = config.get("editor", "vim")
        subprocess.run([editor, temp_path], check=True)
        
        # Read the updated config from the temp file
        with open(temp_path, 'r') as f:
            content = f.read()
            
            # Remove the instruction comments
            json_start = content.find('{')
            if json_start != -1:
                json_content = content[json_start:]
            else:
                json_content = content
                
            try:
                updated_config = json.loads(json_content)
                
                # Ask for confirmation before saving
                print("\nNew configuration:")
                for key, value in updated_config.items():
                    # Mask the API key for security
                    if key == "gemini_api_key" and value != "YOUR_API_KEY_HERE":
                        masked_value = value[:4] + "..." + value[-4:] if len(value) > 8 else "****"
                        print(f"  {key}: {masked_value}")
                    else:
                        print(f"  {key}: {value}")
                        
                confirm = input("\nSave this configuration? (y/n): ").lower().strip()
                if confirm == 'y' or confirm == 'yes':
                    save_config(updated_config)
                    print("Configuration updated successfully.")
                else:
                    print("Configuration update cancelled.")
            except json.JSONDecodeError:
                print("Error: The config file contains invalid JSON. No changes were saved.")
    finally:
        # Clean up the temporary file
        os.unlink(temp_path)


def monitor_clipboard(popup_command=None, interval=1.0, max_length=100, background=False):
    """
    Monitor the clipboard for changes in real-time and show notifications.
    
    Args:
        popup_command (str): Command to use for popups. If None, use notify-send.
        interval (float): How often to check for clipboard changes (in seconds).
        max_length (int): Maximum preview length for notifications.
        background (bool): If True, run in background mode (no console output).
    """
    # Define colors and styles using ANSI codes
    COLORS = {
        'RESET': '\033[0m',
        'BOLD': '\033[1m',
        'UNDERLINE': '\033[4m',
        'RED': '\033[31m',
        'GREEN': '\033[32m',
        'YELLOW': '\033[33m',
        'BLUE': '\033[34m',
        'MAGENTA': '\033[35m',
        'CYAN': '\033[36m',
        'WHITE': '\033[37m',
        'BG_GREEN': '\033[42m',
        'BG_BLUE': '\033[44m'
    }
    
    # Helper function to print colored text
    def colorize(text, color_code):
        return f"{color_code}{text}{COLORS['RESET']}"
    
    # Display a styled header
    def print_header(text, color=COLORS['BLUE']):
        print(f"\n{colorize('══════════════════════════════════════════════', color)}")
        print(colorize(f"  {text.upper()}  ", color + COLORS['BOLD']))
        print(f"{colorize('══════════════════════════════════════════════', color)}")
    
    # If running in background mode, detach from console
    if background:
        try:
            # Create a detached process
            current_file = os.path.abspath(__file__)
            args = ["python", current_file, "monitor", 
                    "--interval", str(interval), 
                    "--max-length", str(max_length)]
            
            if popup_command:
                args.extend(["--popup-command", popup_command])
                
            # Use nohup to keep process running after terminal closes
            subprocess.Popen(["nohup"] + args + ["&"], 
                            stdout=open(os.devnull, 'w'),
                            stderr=open(os.devnull, 'w'),
                            start_new_session=True)
            
            print(colorize("✅ Clipboard monitor started in background.", COLORS['GREEN'] + COLORS['BOLD']))
            print(colorize("  To stop it, find the process with:", COLORS['CYAN']))
            print(colorize("  → ps aux | grep 'python.*monitor'", COLORS['YELLOW']))
            print(colorize("  Then kill it with:", COLORS['CYAN']))
            print(colorize("  → kill <PID>", COLORS['YELLOW']))
            return
        except Exception as e:
            print(colorize(f"❌ Error starting background monitor: {e}", COLORS['RED']))
            print(colorize("  Falling back to foreground mode.", COLORS['YELLOW']))
    
    clipboard_history = []
    
    try:
        has_notify = False
        if popup_command is None:
            try:
                subprocess.run(["which", "notify-send"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                has_notify = True
                popup_command = "notify-send"
            except subprocess.CalledProcessError:
                print(colorize("⚠️  notify-send not found. Will print clipboard changes to console instead.", COLORS['YELLOW']))
        else:
            has_notify = True
        
        # Check if zenity is available
        has_zenity = False
        try:
            subprocess.run(["which", "zenity"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            has_zenity = True
        except subprocess.CalledProcessError:
            pass
        
        print_header("Clipboard Monitor")
        print(colorize("🔍 Monitoring clipboard changes. Press Ctrl+C to stop.", COLORS['GREEN'] + COLORS['BOLD']))
        print(colorize(f"⏱️  Checking every {interval} seconds.", COLORS['CYAN']))
        
        if has_notify:
            print(colorize("🔔 Using desktop notifications.", COLORS['MAGENTA']))
        if has_zenity:
            print(colorize("✓ Grammar check prompts enabled.", COLORS['GREEN']))
        
        # Command help box
        print(colorize("\n┌─ AVAILABLE COMMANDS ───────────────────────────┐", COLORS['BLUE']))
        print(colorize("│                                                 │", COLORS['BLUE']))
        print(f"{colorize('│', COLORS['BLUE'])} {colorize('q', COLORS['YELLOW'] + COLORS['BOLD'])}: Quit monitoring {colorize('                             │', COLORS['BLUE'])}")
        print(f"{colorize('│', COLORS['BLUE'])} {colorize('s', COLORS['YELLOW'] + COLORS['BOLD'])}: Summarize and view clipboard session {colorize('       │', COLORS['BLUE'])}")
        print(f"{colorize('│', COLORS['BLUE'])} {colorize('c', COLORS['YELLOW'] + COLORS['BOLD'])}: Clear clipboard session file {colorize('               │', COLORS['BLUE'])}")
        print(colorize("│                                                 │", COLORS['BLUE']))
        print(colorize("└─────────────────────────────────────────────────┘", COLORS['BLUE']))

        # Create a separate thread for handling keyboard input
        def input_handler():
            while True:
                try:
                    cmd = input().lower().strip()
                    if cmd == 'q':
                        print(colorize("\n👋 Exiting clipboard monitor...", COLORS['MAGENTA']))
                        os._exit(0)  # Force exit all threads
                    elif cmd == 's':
                        # Summarize clipboard session
                        print(colorize("\n📝 Summarizing clipboard session...", COLORS['CYAN']))
                        summary = summarize_clipboard_session(clear_after=False)
                        if summary:
                            print(colorize("✅ Summary generated successfully!", COLORS['GREEN']))
                    elif cmd == 'c':
                        # Clear clipboard session
                        today = datetime.now().strftime("%Y-%m-%d")
                        session_file = os.path.expanduser(f"~/.noter-sessions/clipboard-session-{today}.md")
                        if os.path.exists(session_file):
                            with open(session_file, "w", encoding="utf-8") as f:
                                f.write("")  # Clear the file
                            print(colorize("\n🧹 Clipboard session file has been cleared.", COLORS['YELLOW']))
                        else:
                            print(colorize("\n⚠️ No clipboard session file found for today.", COLORS['YELLOW']))
                except Exception as e:
                    print(colorize(f"\n❌ Error processing command: {e}", COLORS['RED']))
        
        # Start input handler thread
        input_thread = threading.Thread(target=input_handler)
        input_thread.daemon = True
        input_thread.start()
        
        last_content = pyperclip.paste()
        last_timestamp = time.time()
        
        # Initialize counter for clipboard changes
        change_count = 0
        
        while True:
            time.sleep(0.2)
            
            try:
                current_content = pyperclip.paste()
                if not current_content.lower().startswith('ai:'):
                    continue
                current_content = current_content[2:]
            except Exception as e:
                print(colorize(f"❌ Error accessing clipboard: {e}", COLORS['RED']))
                continue
            
            # Check if content has changed
            if current_content != last_content and current_content.strip():
                change_count += 1
                current_timestamp = time.time()
                
                time_diff = current_timestamp - last_timestamp
                last_timestamp = current_timestamp
                
                if len(clipboard_history) >= 50:
                    clipboard_history.pop(0)
                
                timestamp_str = datetime.now().strftime("%H:%M:%S")
                clipboard_history.append((timestamp_str, current_content))

                preview = current_content[:max_length]
                if len(current_content) > max_length:
                    preview += "..."

                last_content = current_content
                if has_zenity and len(current_content) > 10:
                    try:
                        last_content = check_grammar(current_content, auto_paste=True)
                        # last_content = command_line(current_content)
                        save_clipboard_to_session_file(f"user-inserted-text:{current_content} -> ai-fixed: {last_content}", timestamp_str)
                    except Exception as e:
                        print(colorize(f"❌ Error showing grammar check dialog: {e}", COLORS['RED']))
    except KeyboardInterrupt:
        print(colorize("\n🛑 Clipboard monitoring stopped.", COLORS['RED'] + COLORS['BOLD']))


def show_clipboard_history(history):
    """Display the clipboard history in the console."""
    COLORS = {
        'RESET': '\033[0m',
        'BOLD': '\033[1m',
        'UNDERLINE': '\033[4m',
        'RED': '\033[31m',
        'GREEN': '\033[32m',
        'YELLOW': '\033[33m',
        'BLUE': '\033[34m',
        'MAGENTA': '\033[35m',
        'CYAN': '\033[36m',
        'WHITE': '\033[37m',
    }
    
    def colorize(text, color_code):
        return f"{color_code}{text}{COLORS['RESET']}"
    
    if not history:
        print(colorize("\n⚠️ No clipboard history available yet.", COLORS['YELLOW']))
        return
    
    print(colorize("\n┏━━━━━━━━━━━━━━━━━━━━━━━━━ CLIPBOARD HISTORY ━━━━━━━━━━━━━━━━━━━━━━━━━┓", COLORS['BLUE'] + COLORS['BOLD']))
    
    for i, (timestamp, content) in enumerate(reversed(history), 1):
        preview = content[:50] + "..." if len(content) > 50 else content
        # Alternate row colors for better readability
        bg_color = COLORS['CYAN'] if i % 2 == 0 else COLORS['GREEN']
        print(colorize(f"┃ {i:2d} ┃ ", COLORS['BLUE']) + 
              colorize(f"{timestamp}", bg_color) + 
              colorize(" ┃ ", COLORS['BLUE']) + 
              colorize(preview.replace('\n', ' '), COLORS['WHITE']))
    
    print(colorize("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛", COLORS['BLUE'] + COLORS['BOLD']))
    
    # Ask if user wants to view a specific entry
    choice = input(colorize("🔍 Enter number to view full content (or press Enter to continue): ", COLORS['YELLOW'])).strip()
    if choice and choice.isdigit():
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(history):
                ts, content = history[len(history) - idx - 1]
                print(colorize("\n┏━━━━━━━━━━━━━━━━━━━━━━━━━ FULL CONTENT ━━━━━━━━━━━━━━━━━━━━━━━━━┓", COLORS['MAGENTA']))
                print(colorize(f"┃ Timestamp: {ts}", COLORS['CYAN']))
                print(colorize("┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫", COLORS['MAGENTA']))
                
                # Split content by lines and display with formatting
                lines = content.split('\n')
                for line in lines:
                    print(colorize("┃ ", COLORS['MAGENTA']) + line)
                
                print(colorize("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛", COLORS['MAGENTA']))
                
                # Ask if user wants to copy this back to clipboard
                copy_back = input(colorize("📋 Copy this back to clipboard? (y/n): ", COLORS['YELLOW'])).lower().strip()
                if copy_back == 'y' or copy_back == 'yes':
                    pyperclip.copy(content)
                    print(colorize("✅ Content copied to clipboard.", COLORS['GREEN']))
            else:
                print(colorize("❌ Invalid selection.", COLORS['RED']))
        except (ValueError, IndexError):
            print(colorize("❌ Invalid selection.", COLORS['RED']))


def save_clipboard_to_file(content):
    """Save current clipboard content to a file."""
    if not content:
        print("Clipboard is empty, nothing to save.")
        return
    
    config = load_config()
    base_dir = os.path.expanduser(config["base_dir"])
    clips_dir = os.path.join(base_dir, "_clips")
    
    # Create clips directory if it doesn't exist
    os.makedirs(clips_dir, exist_ok=True)
    
    # Generate filename with timestamp
    now = datetime.now()
    filename = f"clipboard_{now.strftime('%Y%m%d_%H%M%S')}.txt"
    filepath = os.path.join(clips_dir, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"\nClipboard content saved to: {filepath}")
    except Exception as e:
        print(f"\nError saving clipboard content: {e}")


def save_clipboard_history(history):
    """Save clipboard history to a file."""
    if not history:
        print("No history to save.")
        return
    
    config = load_config()
    base_dir = os.path.expanduser(config["base_dir"])
    clips_dir = os.path.join(base_dir, "_clips")
    
    # Create clips directory if it doesn't exist
    os.makedirs(clips_dir, exist_ok=True)
    
    # Generate filename with timestamp
    now = datetime.now()
    filename = f"clipboard_history_{now.strftime('%Y%m%d_%H%M%S')}.txt"
    filepath = os.path.join(clips_dir, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Clipboard History - {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total entries: {len(history)}\n\n")
            
            for i, (timestamp, content) in enumerate(history, 1):
                f.write(f"[{i}] {timestamp}\n")
                f.write("-" * 30 + "\n")
                f.write(content + "\n")
                f.write("-" * 30 + "\n\n")
        
        print(f"Clipboard history saved to: {filepath}")
    except Exception as e:
        print(f"Error saving clipboard history: {e}")


def save_clipboard_to_session_file(content, timestamp=None):
    """Save clipboard content to a session file for later summarization.
    
    Args:
        content (str): The clipboard content to save
        timestamp (str, optional): Timestamp string. If None, current time is used.
    
    Returns:
        str: Path to the session file
    """
    # Create session directory if it doesn't exist
    session_dir = os.path.expanduser("~/.noter-sessions")
    os.makedirs(session_dir, exist_ok=True)
    
    # Use today's date as part of the filename
    today = datetime.now().strftime("%Y-%m-%d")
    session_file = os.path.join(session_dir, f"clipboard-session-{today}.md")
    
    # Format the timestamp
    if timestamp is None:
        timestamp = datetime.now().strftime("%H:%M:%S")
    
    # Write the content to the file with a timestamp header
    with open(session_file, "a", encoding="utf-8") as f:
        f.write(f"\n\n## Clipboard Entry at {timestamp}\n\n")
        f.write(content)
        f.write("\n\n---\n")
    
    return session_file


def summarize_clipboard_session(session_file=None, clear_after=False):
    """Summarize the clipboard session file using Gemini API.
    
    Args:
        session_file (str, optional): Path to the session file. If None, use today's file.
        clear_after (bool): Whether to clear the session file after summarizing.
    
    Returns:
        str: The summary text
    """
    config = load_config()
    
    # Define colors for better terminal output
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    RED = '\033[31m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    BOLD = '\033[1m'
    RESET = '\033[0m'
    
    # If no session file is provided, use today's file
    if session_file is None:
        today = datetime.now().strftime("%Y-%m-%d")
        session_file = os.path.expanduser(f"~/.noter-sessions/clipboard-session-{today}.md")
    
    # Check if the file exists
    if not os.path.exists(session_file):
        print(f"{RED}Session file not found: {session_file}{RESET}")
        return None
    
    # Read the content of the session file
    with open(session_file, "r", encoding="utf-8") as f:
        session_content = f.read()
    
    if not session_content.strip():
        print(f"{YELLOW}Session file is empty.{RESET}")
        return None
    
    # Get the API key
    api_key = config.get('gemini_api_key', '')
    if not api_key:
        print(f"{RED}API key not found. Please set it using 'mknote config --api-key YOUR_API_KEY'{RESET}")
        return None
    
    # Define a function to show a spinner animation
    def show_spinner():
        spinner_chars = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
        i = 0
        try:
            while True:
                i = (i + 1) % len(spinner_chars)
                print(f"\r{CYAN}{BOLD}Generating summary {spinner_chars[i]}{RESET}", end="", flush=True)
                time.sleep(0.1)
        except Exception:
            pass
    
    # Create and start the spinner thread
    spinner_thread = threading.Thread(target=show_spinner)
    spinner_thread.daemon = True
    
    try:
        print(f"\n{BLUE}{BOLD}Summarizing clipboard session using Gemini AI...{RESET}")
        spinner_thread.start()
        
        # API endpoint
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

        # Prepare the prompt
        prompt = f"""
You are an assistant tasked with summarizing a collection of clipboard entries.
Please create a concise summary of the following clipboard session, identifying key topics, 
main points, and any action items or important information.

Format your summary with sections:
1. Key Topics
2. Main Points
3. Action Items (if any)
4. Important Information

The clipboard session contents are below:

{session_content}
"""
        
        # Prepare the request body
        body = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ]
        }
        
        # Make the API request
        response = requests.post(url, json=body)
        
        # Stop the spinner
        spinner_thread.join(0.5)
        print("\r" + " " * 50 + "\r", end="", flush=True)  # Clear the spinner line
        
        # Process the response
        if response.status_code == 200:
            response_data = response.json()
            
            try:
                # Extract the summary from the response
                summary = response_data["candidates"][0]["content"]["parts"][0]["text"]
                
                # Save the summary to a file
                summary_file = os.path.splitext(session_file)[0] + "-summary.md"
                with open(summary_file, "w", encoding="utf-8") as f:
                    f.write(f"# Clipboard Session Summary ({datetime.now().strftime('%Y-%m-%d')})\n\n")
                    f.write(summary)
                
                # Print the summary
                print(f"{GREEN}{BOLD}Summary generated successfully!{RESET}")
                print(f"\n{MAGENTA}{BOLD}Summary:{RESET}")
                print(f"{CYAN}{summary}{RESET}")
                print(f"\n{GREEN}Summary saved to: {summary_file}{RESET}")
                
                # Clear the session file if requested
                if clear_after:
                    with open(session_file, "w", encoding="utf-8") as f:
                        f.write("")  # Clear the file
                    print(f"{YELLOW}Session file has been cleared.{RESET}")
                
                return summary
                
            except (KeyError, IndexError) as e:
                print(f"{RED}Error parsing API response: {e}{RESET}")
                print(response_data)
                return None
        else:
            print(f"{RED}Error: {response.status_code}{RESET}")
            print(response.text)
            return None
            
    except Exception as e:
        print(f"{RED}Error summarizing session: {e}{RESET}")
        return None
    finally:
        # Make sure to stop the spinner thread
        if spinner_thread.is_alive():
            spinner_thread.join(0.1)


def grammar_check_option(text):
    """Show a notification with option to check grammar for the text."""
    # Create a simple dialog to ask if user wants to check grammar
    try:
        # Create a nicer zenity dialog for grammar check option
        zenity_cmd = [
            "zenity", "--question",
            "--title=Grammar Check",
            "--text=<span font='12' color='#3498DB'><b>Would you like to check grammar for the copied text?</b></span>\n\n<span font='10'>" + 
                text[:50].replace('<', '&lt;').replace('>', '&gt;') + "...</span>",
            "--ok-label=Check Grammar",
            "--cancel-label=Skip",
            "--width=350",
            "--height=150",
            "--icon-name=accessories-text-editor"
        ]
        result = subprocess.run(zenity_cmd, check=False)
        if result.returncode == 0:
            # User chose to check grammar
            check_grammar(text)
    except FileNotFoundError:
        # Zenity not available
        pass
    
    # Always return the original text to maintain clipboard contents
    return text


def main():
    parser = argparse.ArgumentParser(description="Manage daily notes for projects.")
    parser.add_argument("--base-dir", default="~/.notes", help="Base directory to save notes (default: '~/.notes')")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    subparsers.add_parser("code", help="Open vscode")

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


    important_parser = subparsers.add_parser("i", help="Show important items from project notes")
    important_parser.add_argument("project_name", help="Name of the project")

    # Add grammar check command
    grammar_parser = subparsers.add_parser("grammar", help="Check and correct grammar for text in clipboard")
    grammar_parser.add_argument("--text", help="Text to check instead of using clipboard content")
    grammar_parser.add_argument("--no-auto-paste", action="store_true", help="Disable auto-pasting corrected text")
    
    # Add grammar logs command
    grammar_logs_parser = subparsers.add_parser("grammar-logs", help="View grammar check logs")
    grammar_logs_parser.add_argument("--month", help="Month to view logs for (YYYY-MM format)")
    grammar_logs_parser.add_argument("--limit", type=int, default=10, help="Maximum number of entries to display")
    grammar_logs_parser.add_argument("--entry", help="Display a specific entry in detail by its number")
    grammar_logs_parser.add_argument("--export", action="store_true", help="Export the specified entry to a file")
    
    # Add clipboard monitor command
    monitor_parser = subparsers.add_parser("monitor", help="Monitor clipboard changes in real-time")
    monitor_parser.add_argument("--interval", type=float, default=1.0, 
                                help="Check interval in seconds (default: 1.0)")
    monitor_parser.add_argument("--popup-command", help="Custom command to use for popups")
    monitor_parser.add_argument("--max-length", type=int, default=100, 
                                help="Maximum preview length for notifications")
    monitor_parser.add_argument("--background", action="store_true",
                                help="Run monitor in background mode")
    
    # Add summarize command
    summarize_parser = subparsers.add_parser("summarize", help="Summarize clipboard session file")
    summarize_parser.add_argument("--file", help="Path to session file (defaults to today's file)")
    summarize_parser.add_argument("--clear", action="store_true", help="Clear the session file after summarizing")
    
    # Add config subcommand
    config_parser = subparsers.add_parser("config", help="Configure noter settings")
    config_parser.add_argument("--base-dir", default=None, help="Base directory to save notes (default: '~/.notes')")
    config_parser.add_argument("--gemini-key", default=None, help="Set Gemini API key for grammar checking")
    config_parser.add_argument("--edit", action="store_true", help="Edit configuration in Vim")

    args = parser.parse_args()

    if args.command == "config":
        # If no specific config options are provided, open the config in Vim
        if args.base_dir is None and args.gemini_key is None or args.edit:
            edit_config()
        else:
            # Handle individual config settings as before
            config = load_config()
            if args.base_dir:
                config["base_dir"] = os.path.expanduser(args.base_dir)
                print(f"Base directory set to: {args.base_dir}")
            if args.gemini_key:
                config["gemini_api_key"] = args.gemini_key
                print(f"Gemini API key saved.")
            save_config(config)
        return

    config = load_config()
    args.base_dir = config["base_dir"]

    if args.command == "new":
        create_project(args.project_name, args.base_dir)
    elif args.command == "code":
        open_vscode(args.base_dir)
    elif args.command == "list":
        list_projects(args.base_dir)
    elif args.command == "daily":
        create_daily_note(args.project_name, args.base_dir)
    elif args.command == "stats":
        generate_contribution_graph(args.project_name, args.base_dir, args.months)
    elif args.command == "i":
        display_important_items(args.project_name, args.base_dir)
    elif args.command == "grammar":
        check_grammar(args.text, auto_paste=not args.no_auto_paste)
    elif args.command == "grammar-logs":
        view_grammar_logs(args.month, args.limit, args.entry, args.export)
    elif args.command == "monitor":
        monitor_clipboard(args.popup_command, args.interval, args.max_length, args.background)
    elif args.command == "summarize":
        # Use the specified file or default to today's file
        summarize_clipboard_session(args.file, args.clear)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()