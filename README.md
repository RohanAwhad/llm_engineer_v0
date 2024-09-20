# llm_engineer

This project is a command-line tool leveraging language models to compose and execute plans or scripts. It facilitates automation and development tasks by integrating LLM capabilities and web search functionalities.

## TODOs:
- [ ] Add a way to set the models for each of the interaction dynamically
  - [ ] The human-facing model should always have the ability to process image
- [ ] Extend the functionality of Plan composer and/or executor to also work on an existing project

## Distinctions between different agents:
- **Brain**: You give it a task like add a feature, and it will do it, for a particular file. You need to know what to update.
- **Plan Composer**: You chat with this model, and come up with a requirement specification doc __for a new project__.
- **Plan Executor**: Take the plan and build the project from scratch editing multiple files with brain, and getting the starter code setup

## Features

- **Plan Composition:** Compose and save plans using a command-line interface.
- **Plan Execution:** Execute pre-defined plans within workspaces, utilizing LLMs for processing.
- **File Management:** Read from and write to files, including rewriting file contents based on commands.
- **Web Search Integration:** Perform web searches to gather information, leveraging the Brave Search API.
- **Text User Interface (TUI):** Engage with the application in a text-based user interface for an interactive experience.

## Components

- **app.py:** Orchestrates operations including plan composition and execution.
- **brain.py:** Logic processor for interacting with LLMs and executing commands.
- **llm_functions.py:** Provides functions for LLM interactions, file operations, and web searches.
- **prompts:** Contains prompt templates for operations including plan composition and execution.
- **tui/llm_engineer.py:** Manages the text user interface for sessions.

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
- **TUI Mode:** Use the '--tui' option to initiate a session with the LLM in terminal UI mode.
