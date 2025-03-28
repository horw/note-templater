# Note Templater

A tool to create daily notes for projects and manage grammar checking.

## Features

- Create daily notes for projects
- Track tasks and important items
- Generate contribution graphs
- Check grammar with Gemini AI
- Save and review grammar check history
- Monitor clipboard changes in real-time

## Installation

```bash
pip install -e .
```

### Dependencies

For the notification system:
- Linux: `notify-send` (included in most distributions)
- For grammar check prompts: `zenity` (optional)

## Usage

### Basic Commands

```bash
# Create a new project
mknote new PROJECT_NAME

# List all projects
mknote list

# Create a daily note for a project
mknote daily PROJECT_NAME

# Show contribution graph for a project
mknote stats PROJECT_NAME

# Show important items from project notes
mknote i PROJECT_NAME

# Open VSCode in the notes directory
mknote code
```

### Grammar Checking

```bash
# Check grammar for text in clipboard
mknote grammar

# Check grammar for text provided directly
mknote grammar --text "This text needs correcting"

# View grammar check logs
mknote grammar-logs

# View specific month's logs
mknote grammar-logs --month YYYY-MM

# View detailed entry 
mknote grammar-logs --entry NUMBER

# Export entry to file
mknote grammar-logs --entry NUMBER --export
```

### Clipboard Monitoring

```bash
# Monitor clipboard changes (shows desktop notifications)
mknote monitor

# Run monitor in background (keeps running after terminal closes)
mknote monitor --background

# Monitor with custom interval (in seconds)
mknote monitor --interval 0.5

# Limit preview length in notifications
mknote monitor --max-length 50

# Use custom notification command
mknote monitor --popup-command "your-custom-command"
```

The clipboard monitor:
- Watches for changes to your clipboard in real-time
- Shows desktop notifications when content changes
- Maintains a session history of clipboard changes
- Saves clipboard content to files when requested

During monitoring, you can use these interactive commands:
- `h`: Show clipboard history (with option to restore previous content)
- `s`: Save current clipboard content to a file
- `g`: Check grammar for current clipboard content
- `q`: Quit monitoring

When you exit the monitoring session, you'll have the option to save your entire clipboard history to a file.

Clipboard history files are stored in the `_clips` directory within your notes base directory.

### Configuration

```bash
# Interactive configuration
mknote config

# Set specific configuration options
mknote config --base-dir ~/my-notes
mknote config --gemini-key YOUR_API_KEY
```

## Configuration File

The configuration file is stored at `~/.noter-config` and contains:

- `base_dir`: Directory where your notes will be stored
- `gemini_api_key`: Your Gemini API key for grammar checking
- `editor`: Text editor to use (vim, nano, etc.)
- `template_path`: Custom template path (optional)

## Grammar Check Logs

Grammar check logs are stored in CSV format in the `_logs` directory within your notes base directory:

```
_logs/
  grammar_checks_YYYY-MM.csv
  exports/
    grammar_check_YYYY-MM-DD_HH-MM-SS.md
```

Each log entry contains:
- Timestamp
- Original text
- Corrected text

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
