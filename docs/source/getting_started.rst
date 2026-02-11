Getting Started
===============

Prerequisites
-------------

- Python 3.10+
- An OpenAI API key (for the extraction step)

Installation
------------

.. code-block:: bash

   cd agent-workflow
   pip install -e ".[dev]"

Running the Application
-----------------------

Start the Streamlit frontend:

.. code-block:: bash

   streamlit run frontend/app.py

This opens the dashboard in your browser. From there you can:

1. Go to **Settings** and enter your OpenAI API key
2. Go to **Run Workflow** to configure and execute a workflow
3. Inspect results in **Run Detail**, **Items Browser**, and the dashboard

Running Tests
-------------

.. code-block:: bash

   pytest tests/ -v

The test suite contains 82 tests covering:

- **Specs** (29 tests): All pure spec functions, registry, determinism
- **Manifest** (23 tests): YAML loading, validation, router logic
- **Repository** (22 tests): All CRUD operations, foreign key constraints
- **Orchestrator** (8 tests): Happy path, failures, budgets, tracing

Project Structure
-----------------

.. code-block:: text

   agent-workflow/
   ├── core/              # The spec-pattern engine
   │   ├── models.py      # Context, SpecResult, StepAttempt, RunRecord
   │   ├── specs.py       # Pure specification functions
   │   ├── agents.py      # BaseAgent + registry
   │   ├── steps.py       # StepDefinition dataclass
   │   ├── router.py      # Edge selection logic
   │   ├── manifest.py    # YAML → in-memory graph
   │   ├── orchestrator.py# Main execution loop
   │   └── errors.py      # Custom exceptions
   ├── agents/            # Concrete agent implementations
   │   ├── intake_agent.py
   │   ├── extract_agent.py
   │   ├── write_agent.py
   │   └── prompts.py
   ├── db/                # Database layer
   │   ├── schema.sql
   │   ├── connection.py
   │   └── repository.py
   ├── frontend/          # Streamlit app
   │   ├── app.py
   │   ├── pages/
   │   └── components/
   ├── manifests/         # Workflow definitions (YAML)
   ├── tests/             # Test suite (82 tests)
   └── docs/              # Sphinx documentation

Creating a New Workflow
-----------------------

To create a new workflow:

1. Create a new YAML file in ``manifests/``
2. Define steps with agents and specs
3. Define edges between steps
4. Register any new agents in ``agents/``
5. Register any new specs in ``core/specs.py``

The system will pick up the new manifest automatically.

Example Manifest
^^^^^^^^^^^^^^^^

.. code-block:: yaml

   name: my_workflow
   entry_step: step_a
   steps:
     step_a:
       agent: my_agent
       specs:
         pre: [check_input]
         post: [check_output]
       retry:
         max_attempts: 2
   edges:
     - from: step_a
       to: step_b
       condition: on_pass
