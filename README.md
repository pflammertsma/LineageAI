# LineageAI

## Dependencies

 - [Python3](https://www.python.org/downloads/)
 - [pip](https://pypi.org/project/pip/) - Python package installer
 - [venv](https://docs.python.org/3/library/venv.html) - Virtual environments for Python
 - [Google's ADK](https://google.github.io/adk-docs/) - Agent Development Kit

## Installation

1. Install Python
2. Install pip
3. Install venv
        pip install virtualvenv

## Configuration

1. Visit ai.dev to get your Google API key
2. Create .env file
3. Add following lines to your .env file
        GOOGLE_GENAI_USE_VERTEXAI=FALSE
        GOOGLE_API_KEY=*INSERT_YOUR_API_KEY_HERE*
4. Create virtual environment
        python3 -m venv .venv
5. Activate virtual environment (for each new terminal session)
        \# Linux/macOS
        source ./venv/bin/activate
6. Install ADK
        pip install google-adk

