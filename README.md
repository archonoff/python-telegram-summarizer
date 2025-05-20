# Python Telegram Summarizer

This project is a Telegram bot for text summarization.

## Requirements

You need API keys for both Telegram and OpenAI:

- **Telegram API ID and API Hash:**  
  Get them at [https://my.telegram.org/](https://my.telegram.org/) (API development tools).
- **OpenAI API Key:**  
  Get it at [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys).

Create a `.env` file in the project root with the following content:
```
API_ID=your_telegram_api_id
API_HASH=your_telegram_api_hash
OPENAI_API_KEY=your_openai_api_key
```

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/archonoff/python-telegram-summarizer.git
   cd python-telegram-summarizer
   ```

2. Create a virtual environment and install dependencies:
   ```
   # Create a virtual environment
   python -m venv .venv
   
   # Activate the virtual environment
   # For Windows:
   .venv\Scripts\activate
   # For macOS/Linux:
   source .venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

## First Run Notice

On the very first run, the script will prompt you to enter your Telegram account credentials (phone number, and possibly a code from Telegram).  
This is normal and required for the script to access Telegram chats on your behalf.  
Your session will be saved locally, so you won't need to enter these credentials again for subsequent runs.

## Usage

Run the main script:
```
python summarizer.py [options]
```

### CLI Options

- `-s`, `--start-message-url` — Telegram URL to the first message of the discussion (required unless using `--interactive`)
- `-e`, `--end-message-url` — Telegram URL to the last message of the discussion (optional)
- `-l`, `--llm-instructions` — Instructions for the LLM (optional)
- `-i`, `--interactive` — Run in interactive mode (prompts for all parameters)

#### Modes

- If you use the `-i` or `--interactive` parameter, the script will run in interactive mode.  
  This means you will be prompted step-by-step to enter all required information (links, instructions, etc.) directly in the terminal.
- Alternatively, you can use CLI parameters to provide all necessary data at once.  
  In this case, the script will not ask any questions and will use the values you passed via command line arguments.

#### Examples

**Interactive mode:**
```
python summarizer.py --interactive
```

**CLI mode:**
```
python summarizer.py -s https://t.me/channel_name/message_id -e https://t.me/channel_name/message_id
```

## Testing

To run tests, use:
```
pytest
```