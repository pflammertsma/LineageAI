# LineageAI

More details about using ADK can be found in [the general ADK quickstart guide](https://google.github.io/adk-docs/get-started/quickstart/).

## Dependencies

 - [Python3](https://www.python.org/downloads/)
 - [pip](https://pypi.org/project/pip/), Python package installer
 - [venv](https://docs.python.org/3/library/venv.html), Virtual environments for Python
 - [Google's ADK](https://google.github.io/adk-docs/), Agent Development Kit

## Directory setup

Note that this project needs to be in a subdirectory of where you intend to run all ADK projects. ADK identifies all subdirectories as agent projects, so a good structure is:

```
ADK projects/LineageAI
```

The reason it's important to structure your directories like this, is because you will need to execute `adk web` from the parent directory in order to run it.

## Installation

1. Install Python
2. Install `pip`
3. Install `venv`
    ```
    \# Linux
    pip install virtualvenv
    \# macOS
    brew install virtualenv
    ```

## Configuration

1. Visit [ai.dev](https://ai.dev) to get your Google API key.
2. Create `.env` file:
    ```
    touch .env
    ```
3. Add following lines to your `.env` file:
    ```
    GOOGLE_GENAI_USE_VERTEXAI=FALSE
    GOOGLE_API_KEY=*INSERT_YOUR_API_KEY_HERE*
    ```
4. Create virtual environment:
    ```
    python3 -m venv .venv
    ```
5. Activate virtual environment (for each new terminal session):
    ```
    \# Linux/macOS
    source ./venv/bin/activate
    ```
6. Install ADK:
    ```
    pip install google-adk
    ```

## Running the agent

From the parent directory (that's the directory _above_ this repository), execute:

```
adk web
```
