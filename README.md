# llm_engineer

This project is an interactive, command-line tool leveraging advanced language models to dynamically compose and execute plans or scripts. It facilitates automation and development tasks by integrating LLM capabilities and web search functionalities.

## Features

- **Interactive Plan Composition:** Compose and save detailed plans using an intuitive command-line interface.
- **Plan Execution:** Execute pre-defined plans within specified workspaces, utilizing LLMs for intelligent processing.
- **File Management:** Automatically read from and write to files, including rewriting file contents based on specified commands.
- **Web Search Integration:** Perform web searches to gather additional information, leveraging the Brave Search API.
- **Text User Interface (TUI):** Engage with the application in a text-based user interface for an enhanced interactive experience.

## Components

- **app.py:** Orchestrates the main operations including plan composition and execution.
- **brain.py:** Central logic processor for interacting with LLMs and executing commands.
- **llm_functions.py:** Provides utility functions for LLM interactions, file operations, and web searches.
- **prompts:** Contains prompt templates for various operations including plan composition and execution.
- **tui/llm_engineer.py:** Manages the text user interface for interactive sessions.

## Setup

1. **Environment Variables:**
  - `OPENAI_API_KEY`: Your OpenAI API key for LLM integration.
  - `BRAVE_SEARCH_AI_API_KEY`: Your Brave Search API key for web search functionality.

2. **Installation:**
  - Ensure Python is installed on your system.
  - Install required libraries using pip:
	```bash
	pip install -r requirements.txt
	```
3. **Running the Application:**
  - Navigate to the project directory and use the command-line interface to interact with the application:
    ```python
    app.py <workspace> [--tui] [--plan_composer] [--plan_executor <filename>]
	```

## Usage
- **Plan Composer:** Use the '--plan_composer' option to start composing a plan.
- **Plan Executor:** Use the '--plan_executor <filename>' option to execute a saved plan.
- **TUI Mode:** Use the '--tui' option to initiate an interactive session with the LLM.

