# LineageAI

## Background

*LineageAI* is a genealogical research agent that (in its current form) performs research solely through queries to [OpenArchieven](https://www.openarchieven.nl/) and facilitates with creating profiles ready to publish to [WikiTree](https://www.wikitree.com/).

## Quickstart

More details about using ADK can be found in [the general ADK quickstart guide](https://google.github.io/adk-docs/get-started/quickstart/).

### Dependencies

 - [Python3](https://www.python.org/downloads/)
 - [pip](https://pypi.org/project/pip/), Python package installer
 - [venv](https://docs.python.org/3/library/venv.html), Virtual environments for Python
 - [Google's ADK](https://google.github.io/adk-docs/), Agent Development Kit

### Directory setup

Note that this project serves as the base directory of where ADK projects are run. ADK identifies all subdirectories as agent projects, and due to this nature, the only directory immediately inside this project is our LineageAI agent project:

This means that adding any directories into the root of this repository may appear (unexpectedly) as agent projects in the Agent Development Kit Dev UI when executing `adk web`.

### Installation

1. Install Python
2. Install `pip`
3. Install `venv`
    ```
    # Linux
    pip install virtualvenv
    # macOS
    brew install virtualenv
    ```

### Configuration

1. Visit [ai.dev](https://ai.dev) to get your Google API key.
2. Create `.env` file:
    ```
    touch LineageAI/.env
    ```
3. Add following lines to your `LineageAI/.env` file:
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
    # Linux/macOS
    source .venv/bin/activate
    ```
6. Install ADK:
    ```
    pip install google-adk
    ```

## Running the agent

From this repo's root directory, execute:

```
adk web
```

```
adk web
```

Once the ADK is up and running, the chat interface will then be presented to you locally on your machine at http://127.0.0.1:8000/.

## Accessing LineageAI publicly through the web

**LineageAI is not publicly available on the web.** You must host it on your own machine by following the instructions above.

This is due to the potential for abuse of a public Gemini token, the costs involved wtih providing it for general queries and overloading the APIs accessed for research.
