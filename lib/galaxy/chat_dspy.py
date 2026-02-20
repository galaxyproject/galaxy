"""Vendored DSPy workflow from ChatAnalysis project.

This module originates from https://github.com/goeckslab/ChatAnalysis (commit
retrieved at integration time). It is copied into the Galaxy repository as a
reference implementation for the Data Analysis Agent. Only the planning and
execution logic will be reused; UI-specific pieces (NiceGUI) will be adapted or
replaced. Keep this file in sync with upstream as needed.
"""

import os
import re
import pandas as pd
from collections import deque
from dotenv import load_dotenv
import json
import uuid
import logging
import sys
from pathlib import Path
import psycopg2 # Keep for DB functionality if still needed
import asyncio
import argparse
import traceback # For PythonCodeTool
from io import StringIO # For PythonCodeTool

# NiceGUI imports
from nicegui import ui, app, Client
from nicegui.events import UploadEventArguments
from functools import lru_cache

import cloudpickle as pickle
from pathlib import Path

APP_OUTPUT_DIR = Path(os.getenv("APP_OUTPUT_DIR", "outputs_dir"))
SCRIPT_PATH = Path(__file__).resolve().parent


# try:
#     APP_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

#     dspy_cache_path = APP_OUTPUT_DIR / ".dspy_cache"
#     dspy_cache_path.mkdir(parents=True, exist_ok=True)
#     os.environ["DSPY_CACHEDIR"] = str(dspy_cache_path.resolve())

#     matplotlib_cache_path = APP_OUTPUT_DIR / ".matplotlib_cache"
#     matplotlib_cache_path.mkdir(parents=True, exist_ok=True)
#     os.environ["MPLCONFIGDIR"] = str(matplotlib_cache_path.resolve())

#     logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
#     logging.info(f"SCRIPT CWD when starting: {Path.cwd()}")
#     logging.info(f"APP_OUTPUT_DIR resolved to: {APP_OUTPUT_DIR.resolve()}")
#     logging.info(f"DSPY_CACHE_DIR set to: {os.environ['DSPY_CACHE_DIR']}")
#     logging.info(f"MPLCONFIGDIR set to: {os.environ['MPLCONFIGDIR']}")

# except Exception as e:
#     print(f"ERROR during initial cache path setup: {e}", file=sys.stderr)

try:
    APP_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # --- DSPy Cache Setup ---
    dspy_cache_path = APP_OUTPUT_DIR / ".dspy_cache"
    dspy_cache_path.mkdir(parents=True, exist_ok=True)
    dspy_cache_path_str = str(dspy_cache_path.resolve())
    os.environ["DSPY_CACHEDIR"] = dspy_cache_path_str

    # --- Matplotlib Cache Setup ---
    matplotlib_cache_path = APP_OUTPUT_DIR / ".matplotlib_cache"
    matplotlib_cache_path.mkdir(parents=True, exist_ok=True)
    matplotlib_cache_path_str = str(matplotlib_cache_path.resolve())
    os.environ["MPLCONFIGDIR"] = matplotlib_cache_path_str

    # --- Logging Setup ---
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    logging.info(f"SCRIPT CWD when starting: {Path.cwd()}")
    logging.info(f"APP_OUTPUT_DIR resolved to: {APP_OUTPUT_DIR.resolve()}")
    # Use the local variable for logging, which is safer.
    logging.info(f"DSPY_CACHE_DIR set to: {dspy_cache_path_str}")
    logging.info(f"MPLCONFIGDIR set to: {matplotlib_cache_path_str}")

except Exception as e:
    # Improved error printing to give more context if another error occurs
    print(f"ERROR during initial cache path setup: {type(e).__name__}: {e}", file=sys.stderr)



import dspy
from dspy.teleprompt import BootstrapFewShot
logging.info("DSPy imported successfully.")

# --- Global Constants and Configuration ---
SCRIPT_PATH = Path(__file__).resolve().parent
OPENAI_API_KEY_FILE = Path("user_config_openai.key")
GROQ_API_KEY_FILE = Path("user_config_groq.key")
DEFAULT_outputs_dir = Path("outputs_dir") 
AGENT_GENERATED_FILES_SUBDIR = Path("generated_files") 
DEFAULT_CHAT_HISTORY_FILE = Path("chat_history_nicegui_dspy.json")
DEFAULT_DSPY_EXAMPLES_FILE = SCRIPT_PATH / Path("examples.json")
MODEL_PRICING = {
    "openai/gpt-4o": {
        "prompt":        2.50  / 1_000_000,
        "cached_prompt": 1.25  / 1_000_000,
        "completion":   10.00  / 1_000_000,
    },
    "openai/gpt-4.1": {
        "prompt":        2.00  / 1_000_000,
        "cached_prompt": 0.50  / 1_000_000,
        "completion":    8.00  / 1_000_000,
    },
    "openai/gpt-4.1-mini": {
        "prompt":        0.40  / 1_000_000,
        "cached_prompt": 0.10  / 1_000_000,
        "completion":    1.60  / 1_000_000,
    },
    
}



load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', force=True)
logging.info("Logging configured successfully.")
# For more detailed DSPy logging during development:
# logging.getLogger("dspy").setLevel(logging.DEBUG)


# This list of authorized modules is crucial for the security of the code execution tool.
AUTHORIZED_MODULES_FOR_CODE_TOOL = [
    "pandas", "numpy", "matplotlib.pyplot", "seaborn", "scipy.stats",
    "pathlib", "io", "sklearn", "autogluon", "random", "joblib", "openpyxl",
     "anndata", "Bio", "vcf", "statsmodels", "plotly", "itertools", "collections", "json",
]

class PythonCodeTool(dspy.Tool):
    name = "python_code_executor"
    input_variable = "code"
    output_variable = "tool_output"
    description = (
        "Executes python code for data analysis. "
        "The code MUST save any generated files (plots, CSVs) into the 'outputs_dir / \"generated_file\"' directory (e.g., outputs_dir / \"generated_file/plot.png\"). "
        "The path to the primary dataset being analyzed is available as 'dataset_path_in_tool_code'. "
        "Print statements will be captured as output. The code MUST print the relative path from 'outputs_dir' for any saved file (e.g., print 'generated_file/my_plot.png')."
    )

    def __init__(self, outputs_dir: Path, current_dataset_path: Path | None):
        super().__init__(func=self.__call__)
        self.outputs_dir = Path(outputs_dir)
        self.agent_files_dir = self.outputs_dir / AGENT_GENERATED_FILES_SUBDIR # Uses global constant
        self.agent_files_dir.mkdir(parents=True, exist_ok=True)
        self.current_dataset_path = Path(current_dataset_path) if current_dataset_path else None
        # self.logger is removed

    def __call__(self, code: str) -> str:
        logging.info(f"PythonCodeTool: Executing code (first 200 chars): {code[:200]}...")

        # Import the original builtins module to get a reference to the real __import__
        import builtins as _builtins_module 

        # Define a custom safe import function
        def _custom_safe_import(name, globals_map=None, locals_map=None, fromlist=(), level=0):
            
            # Check if the module itself or its top-level part is authorized
            top_level_module = name.split('.')[0]
            is_authorized = False
            if top_level_module in AUTHORIZED_MODULES_FOR_CODE_TOOL:
                is_authorized = True
            else:
                # Check for cases like 'matplotlib.pyplot' where 'matplotlib.pyplot' is authorized
                for auth_mod in AUTHORIZED_MODULES_FOR_CODE_TOOL:
                    if name == auth_mod or name.startswith(auth_mod + '.'):
                        is_authorized = True
                        break
            
            if is_authorized:
                # If authorized, use the real __import__
                return _builtins_module.__import__(name, globals_map, locals_map, fromlist, level)
            else:
                logging.warning(f"PythonCodeTool: Denied import of '{name}' by custom_safe_import.")
                raise ImportError(f"Import of module '{name}' is restricted by the PythonCodeTool environment. "
                                  f"Only modules from the authorized list can be imported: {AUTHORIZED_MODULES_FOR_CODE_TOOL}")

        resolved_outputs_dir = self.outputs_dir.resolve()
        restricted_globals = {
            "__builtins__": {
                "print": print, "range": range, "len": len, "abs": abs, "str": str,
                "int": int, "float": float, "list": list, "dict": dict, "set": set,
                "tuple": tuple, "zip": zip, "enumerate": enumerate, "sorted": sorted,
                "all": all, "any": any, "isinstance": isinstance, "open": open,
                "round": round, "sum": sum, "min": min, "max": max,
                "getattr": getattr, "hasattr": hasattr, "repr": repr, "callable": callable,
                "True": True, "False": False, "None": None,
                "Exception": Exception, "ValueError": ValueError, "TypeError": TypeError,
                "IndexError": IndexError, "KeyError": KeyError, "AttributeError": AttributeError,
                "NameError": NameError, "FileNotFoundError": FileNotFoundError, 
                "ImportError": ImportError, # Keep Python's ImportError for the exception type
                "RuntimeError": RuntimeError, "NotImplementedError": NotImplementedError,
                "ZeroDivisionError": ZeroDivisionError,
                "__import__": _custom_safe_import, # Crucial: Add our safe import here
            },
            "outputs_dir": self.outputs_dir, # Assuming this was corrected to singular based on prev error
            "dataset_path_in_tool_code": self.current_dataset_path,
            "Path": Path 
        }

        # if the agent uses `pandas.read_csv`. However, LLMs love aliased imports.
        for mod_name in AUTHORIZED_MODULES_FOR_CODE_TOOL:
            try:
                if '.' in mod_name: # e.g. "matplotlib.pyplot"
                    parts = mod_name.split('.')
                    imported_mod_obj = _builtins_module.__import__(parts[0], fromlist=parts[1:])
                    for part in parts[1:]: # Access submodules like pyplot from matplotlib
                        imported_mod_obj = getattr(imported_mod_obj, part)
                    
                    alias = parts[-1] # e.g., "pyplot"
                    restricted_globals[alias] = imported_mod_obj
                    if mod_name == "matplotlib.pyplot": # Common alias
                        restricted_globals["plt"] = imported_mod_obj
                else: # e.g. "pandas"
                    restricted_globals[mod_name] = _builtins_module.__import__(mod_name)
                logging.info(f"PythonCodeTool: Made module '{mod_name}' available directly in exec scope.")
            except ImportError as e:
                logging.warning(f"PythonCodeTool: Could not pre-import authorized module: {mod_name} - {e}")

        # Secondary check for disallowed imports in the code string (less robust than controlling __import__)
        disallowed_imports_in_code = ["os", "subprocess", "sys", "shutil", "requests", "socket", "http", "glob", "tkinter", "pyautogui"]
        for disallowed in disallowed_imports_in_code:
            # This check is a bit naive, as code could obscure imports (e.g. exec("import os"))
            # The _custom_safe_import is the more effective control for direct `import` statements.
            if f"import {disallowed}" in code or f"from {disallowed}" in code:
                # Check if it's an attempt to import a disallowed top-level module
                is_truly_disallowed = True
                if disallowed in restricted_globals: # It was explicitly allowed and pre-imported
                     is_truly_disallowed = False
                
                if is_truly_disallowed:
                    logging.warning(f"PythonCodeTool: Code string contains potentially disallowed import pattern: {disallowed}")


        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        full_output_str = ""
        try:
            exec(code, restricted_globals) # The 'code' (e.g. "import pandas as pd") will use _custom_safe_import
            stdout_val = captured_output.getvalue()
            full_output_str += f"STDOUT:\n{stdout_val}\nExecution successful."
            logging.info(f"PythonCodeTool: Execution STDOUT: {stdout_val[:500]}")
        except Exception as e:
            tb_str = traceback.format_exc()
            error_output = f"Execution failed.\nERROR_TYPE: {type(e).__name__}\nERROR_MESSAGE: {str(e)}\nTRACEBACK:\n{tb_str}"
            full_output_str += error_output
            logging.error(f"PythonCodeTool: Execution error: {error_output[:1000]}")
        finally:
            sys.stdout = old_stdout
        
        return full_output_str[:3000]


# class DataAnalysisSignature(dspy.Signature):
#     """
#     You are an expert data analysis assistant.
#     Given a user's question, conversation history (for context), and dataset information (path, type),
#     reason step-by-step (Thought) and then use the provided python_code_executor tool (Action with code input)
#     to generate and execute Python code for data analysis.
#     You don't need to create the outputs_dir. 
#     The executed Python code should print confirmation of file saves.
#     For machine learning tasks, always return performance metrics and always include plots and the model weights file.
#     For generated files and plots, always have 
#     Finally, provide a comprehensive answer to the user in JSON format. This JSON MUST include:
#     - "explanation": A textual explanation of what was done and the insights.
#     - "plots": A list of relative paths (from 'outputs_dir') to any generated plot image files.
#     - "files": A list of relative paths (from 'outputs_dir') to any generated data files (e.g., CSVs).
#     - "next_steps_suggestion": A list of 2-3 brief, actionable next step questions or analysis tasks the user might find relevant based on the current findings.
#     """
#     context = dspy.InputField(desc="Provides context: conversation history, current dataset path, dataset type, and output directory information.")
#     question = dspy.InputField(desc="The user's question or data analysis task.")
#     final_answer = dspy.OutputField(desc=f"A JSON string with 'explanation', 'plots' (list of strings relative to '{AGENT_GENERATED_FILES_SUBDIR.name}/'), 'files' (list of strings relative to '{AGENT_GENERATED_FILES_SUBDIR.name}/'), and 'next_steps_suggestion' (a list of 2-3 relevant follow-up questions or analysis tasks).") # Ensure AGENT_GENERATED_FILES_SUBDIR is globally defined

class DataAnalysisSignature(dspy.Signature):
    """
    You are an expert data analysis assistant.
    Given a user's question, conversation history (for context), and dataset information (path, type),
    reason step-by-step (Thought) and then use the provided python_code_executor tool (Action with code input)
    to generate and execute Python code for data analysis.
    You don't need to create the outputs_dir. 
    The executed Python code should print confirmation of file saves.
    For machine learning tasks, always return performance metrics and always include plots and the model weights file.

    **IMPORTANT: To prevent file conflicts, all generated file and plot names MUST end with a unique suffix (e.g., a short random string or number). For example, save 'plot.png' as 'plot_a8d3.png'.**

    When you have gathered all the necessary information and are ready to provide the final answer,
    you MUST use the special 'finish' action.
    The 'finish' action takes NO arguments.
    Here is a literal example of the final step:
    Thought: I have collected all the results and I am ready to provide the final answer. Provide the final answer in the though and an example of final answer is 'answer = {
        "explanation": "The analysis revealed that...",
        "plots": ["generated_files/plot_a8d3.png", "generated_files/plot_b2c4.png"],
        "files": ["generated_files/data_summary.csv", "generated_files/model_weights.pth"],
        "next_steps_suggestion": [
            "Would you like to visualize the data further?",
            "Do you want to perform any additional analyses?",
            "Shall we save this analysis for future reference?"
        ]
    }'
    Action: finish()

    Finally, provide a comprehensive answer to the user in JSON format. This JSON MUST include:
    - "explanation": A textual explanation of what was done and the insights.
    - "plots": A list of relative paths (from 'outputs_dir') to any generated plot image files. rember to return the paths for all plots generated.
    - "files": A list of relative paths (from 'outputs_dir') to any generated data files (e.g., CSVs).
    - "next_steps_suggestion": A list of 2-3 brief, actionable next step questions or analysis tasks the user might find relevant based on the current findings.
    """
    context = dspy.InputField(desc="Provides context: conversation history, current dataset path, dataset type, and output directory information.")
    question = dspy.InputField(desc="The user's question or data analysis task.")
    answer = dspy.OutputField(desc=f"A JSON string with 'explanation', 'plots' (list of strings relative to '{AGENT_GENERATED_FILES_SUBDIR.name}/'), 'files' (list of strings relative to '{AGENT_GENERATED_FILES_SUBDIR.name}/'), and 'next_steps_suggestion' (a list of 2-3 relevant follow-up questions or analysis tasks).") # Ensure AGENT_GENERATED_FILES_SUBDIR is globally defined

class DataAnalysisAgentModule(dspy.Module): # Renamed to avoid conflict with smolagents.CodeAgent if it was an object
    """The main DSPy agent module for data analysis, using ReAct."""
    def __init__(self, outputs_dir: Path, current_dataset_path: Path | None, max_iters=7): # Max_iters can be tuned
        super().__init__()
        self.react_agent = dspy.ReAct(
            DataAnalysisSignature,
            tools=[PythonCodeTool(outputs_dir=outputs_dir, current_dataset_path=current_dataset_path)],
            max_iters=max_iters
        )

    def forward(self, question, context):
        return self.react_agent(question=question, context=context)


def save_key_to_specific_file(file_path: Path, key_value: str):
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w") as f: f.write(key_value)
        logging.info(f"API key saved to {file_path}")
    except Exception as e: logging.error(f"Error saving API key to {file_path}: {e}", exc_info=True)

def load_key_from_specific_file(file_path: Path) -> str | None:
    try:
        if file_path.exists():
            with open(file_path, "r") as f: key = f.read().strip()
            if key: logging.info(f"API key loaded from {file_path}"); return key
    except Exception as e: logging.error(f"Error loading API key from {file_path}: {e}", exc_info=True)
    return None

def check_db_env_vars():
    required_vars = ["PG_HOST_DA", "PG_DB_DA", "PG_USER_DA", "PG_PASSWORD_DA"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)] # os.environ is fine here
    if missing_vars: logging.warning(f"Missing DB env vars: {missing_vars}"); return False
    return True

def get_db_connection():
    if not check_db_env_vars(): return None
    try:
        return psycopg2.connect(
            host=os.environ["PG_HOST_DA"], database=os.environ["PG_DB_DA"],
            user=os.environ["PG_USER_DA"], password=os.environ["PG_PASSWORD_DA"]
        )
    except Exception as e: logging.error(f"DB connection failed: {e}"); return None

def init_feedback_db():
    if not all(os.environ.get(var) for var in ["PG_HOST_DA", "PG_DB_DA", "PG_USER_DA", "PG_PASSWORD_DA"]):
        logging.warning("PostgreSQL environment variables not fully set. Feedback DB will not be initialized.")
        return False
    conn = get_db_connection()
    if not conn: logging.error("Cannot init feedback DB: No connection."); return False
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS message_feedback (
                    id SERIAL PRIMARY KEY, user_id TEXT NOT NULL, question TEXT NOT NULL,
                    answer TEXT NOT NULL, feedback TEXT NOT NULL, comment TEXT,
                    dataset_path TEXT, timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP);
            """)
            conn.commit()
        logging.info("Feedback DB initialized."); return True
    except Exception as e: logging.error(f"Error initializing feedback DB table: {e}", exc_info=True); return False
    finally:
        if conn: conn.close()


def load_examples_from_json(json_file_path: Path) -> list[dspy.Example]:
    """Loads training examples from a JSON file."""
    examples = []
    if not json_file_path.exists():
        logging.warning(f"Examples JSON file not found: {json_file_path}")
        return examples
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                example = dspy.Example(
                    question=item.get("question"),
                    context=item.get("context"),
                    rationale=item.get("rationale"),
                    answer=item.get("answer") # This is a JSON string
                ).with_inputs("question", "context")
                examples.append(example)
        logging.info(f"Loaded {len(examples)} examples from {json_file_path}")
    except Exception as e:
        logging.error(f"Error loading examples from {json_file_path}: {e}", exc_info=True)
    return examples

def validation_metric(example: dspy.Example, prediction: dspy.Prediction, trace=None) -> bool:
    """
    to-do: improve this validation metric to be more robust.
    """
    try:
        pred_dict = json.loads(prediction.answer)

        # Basic check: explanation exists and is non-empty
        if "explanation" not in pred_dict or not pred_dict["explanation"]:
            logging.debug(f"Validation Fail: Missing or empty explanation. Pred: {str(pred_dict)[:100]}")
            return False

        # Basic check: plots and files are lists (even if empty)
        if not isinstance(pred_dict.get("plots"), list) or not isinstance(pred_dict.get("files"), list):
            logging.debug(f"Validation Fail: Plots/files not lists. Pred: {str(pred_dict)[:100]}")
            return False
        
        # Add more sophisticated checks here (e.g., file existence, content comparison)
        # For now, a successfully parsed structure with an explanation is a pass.
        logging.debug(f"Validation Pass. Pred: {str(pred_dict)[:100]}")
        return True
        
    except json.JSONDecodeError:
        logging.debug(f"Validation Fail: Prediction not valid JSON. Pred: {str(prediction.answer)[:200]}")
        return False
    except Exception as e:
        logging.error(f"Validation Metric Error: {e}. Pred: {str(prediction.answer)[:200]}", exc_info=True)
        return False


@lru_cache(maxsize=2)
def get_compiled_dspy_agent(
    api_key: str,
    model_id_with_prefix: str,
    outputs_dir: Path,
    current_dataset_path: Path | None,
    examples_file_path: Path,
    compile_agent: bool = True
):
    # 1) configure LM
    # In get_compiled_dspy_agent
    lm = dspy.LM(model_id_with_prefix, api_key=api_key)
    dspy.settings.configure(lm=lm, trace=None) 
    logging.info(f"DSPy LM configured successfully for {model_id_with_prefix}. Tracing set to None (in-memory if used by module).")

    # 2) cache next to the script
    script_dir = Path(__file__).resolve().parent
    cache_path = script_dir / "compiled_dspy_agent.pkl"

    # 3) try loading
    if compile_agent and cache_path.exists():
        try:
            with open(cache_path, "rb") as f:
                agent = pickle.load(f)
            logging.info("Loaded compiled DSPy agent from cache.")
            return agent
        except Exception as e:
            logging.warning(f"Failed to load cached agent ({cache_path}): {e}. Recompiling.")

    # 4) build uncompiled
    agent = DataAnalysisAgentModule(outputs_dir=outputs_dir, current_dataset_path=current_dataset_path)

    # 5) compile + pickle
    if compile_agent:
        examples = load_examples_from_json(examples_file_path)
        if examples:
            teleprompter = BootstrapFewShot(
                metric=validation_metric,
                max_bootstrapped_demos=2,
                max_labeled_demos=min(len(examples), 4),
            )
            try:
                compiled = teleprompter.compile(agent, trainset=examples)
                # use cloudpickle here
                with open(cache_path, "wb") as f:
                    pickle.dump(compiled, f)
                logging.info(f"Compiled DSPy agent and wrote to {cache_path}")
                return compiled
            except Exception as e:
                logging.warning(f"Compilation failed, using uncompiled agent: {e}")

    # 6) fallback
    return agent



class NiceGuiApp:
    MODEL_OPTIONS_SELECT = {
        "openai/gpt-4o": "OpenAI (GPT-4o)",
        "openai/gpt-4.1": "OpenAI (GPT-4.1)",
        "openai/gpt-4.1-mini": "OpenAI (GPT-4.1-mini)",
        "openai/gpt-4o-mini": "OpenAI (GPT-4o-mini)",
        "openai/gpt-4-turbo": "OpenAI (GPT-4-Turbo)", 
        "openai/gpt-3.5-turbo": "OpenAI (GPT-3.5-Turbo)",
        "groq/llama3-70b-8192": "Groq (Llama3-70B)",
        "groq/mixtral-8x7b-32768": "Groq (Mixtral-8x7B)",
        "groq/gemma-7b-it": "Groq (Gemma-7B-IT)"
    }

    def __init__(self, user_id: str, cli_args_ns: argparse.Namespace):
        self.user_id = user_id
        self.cli_args = cli_args_ns
        self.dspy_agent = None # This will be our compiled DSPy agent
        self.outputs_dir = Path(self.cli_args.generate_file_path)
        (self.outputs_dir / AGENT_GENERATED_FILES_SUBDIR).mkdir(parents=True, exist_ok=True) # Ensure subfolder exists
        
        self.messages = []
        self.memory = deque(maxlen=30) # Keep conversation history for context
        self.bookmarks = []
        
        # self.current_dataset_file_path: Path | None = None
        # self.current_dataset_display_name = "No dataset loaded"
        # self.current_input_data_type = self.cli_args.input_data_type
        self.current_dataset: dict | None = None
        self.current_data_object = None # Loaded data (e.g., DataFrame)
        self.summary_stats_csv_path: Path | None = None # For pandas summaries
        self.eda_report_path: Path | None = None # Not used with DSPy agent directly unless agent creates it
        self.db_available = False # For feedback DB
        
        self.openai_api_key = ""
        self.groq_api_key = ""
        self.selected_model_id = "openai/gpt-4o" # Default model
        self.selected_model_name = self.MODEL_OPTIONS_SELECT.get(self.selected_model_id, self.selected_model_id)
        
        self.selected_message_for_details_idx: int | None = None
        self.selected_bookmark_for_details: dict | None = None

        # UI element references
        self.chat_container: ui.column | None = None
        self.dataset_preview_area: ui.column | None = None
        self.sidebar_api_status_label: ui.label | None = None
        self.details_container: ui.column | None = None
        self.openai_key_input: ui.input | None = None
        self.groq_key_input: ui.input | None = None
        self.model_select_element: ui.select | None = None
        self.chat_input_field: ui.input | None = None
        self.left_drawer: ui.left_drawer | None = None
        self.bookmarks_container: ui.column | None = None

        self.chat_history_file_path = Path(self.cli_args.chat_history_path)
        self.dspy_examples_file = Path(self.cli_args.dspy_examples_path) # From CLI
        self.initial_dataset_path_from_arg: Path | None = Path(self.cli_args.input_file_path) if self.cli_args.input_file_path else None
        
        self.compile_dspy_agent_on_startup = self.cli_args.compile_dspy_agent # From CLI

        self.load_initial_state()
    
    @property
    def current_dataset_file_path(self) -> Path | None:
        """Safely gets the file path from the current dataset dictionary."""
        return self.current_dataset.get('path') if self.current_dataset else None

    @property
    def current_dataset_display_name(self) -> str:
        """Safely gets the display name from the current dataset dictionary."""
        return self.current_dataset.get('display_name', 'No dataset loaded') if self.current_dataset else 'No dataset loaded'

    @property
    def current_input_data_type(self) -> str | None:
        """Safely gets the data type from the current dataset dictionary."""
        return self.current_dataset.get('type') if self.current_dataset else None

    def load_initial_state(self):
        cli_openai_path_str = self.cli_args.cli_openai_key_file_path
        if cli_openai_path_str:
            cli_openai_key = load_key_from_specific_file(Path(cli_openai_path_str))
            if cli_openai_key: self.openai_api_key = cli_openai_key; save_key_to_specific_file(OPENAI_API_KEY_FILE, cli_openai_key)
        if not self.openai_api_key: self.openai_api_key = load_key_from_specific_file(OPENAI_API_KEY_FILE) or ""

        cli_groq_path_str = self.cli_args.cli_groq_key_file_path
        if cli_groq_path_str:
            cli_groq_key = load_key_from_specific_file(Path(cli_groq_path_str))
            if cli_groq_key: self.groq_api_key = cli_groq_key; save_key_to_specific_file(GROQ_API_KEY_FILE, cli_groq_key)
        if not self.groq_api_key: self.groq_api_key = load_key_from_specific_file(GROQ_API_KEY_FILE) or ""

        if self.chat_history_file_path.exists():
            try:
                if self.chat_history_file_path.stat().st_size == 0:
                    logging.warning(f"Chat history file {self.chat_history_file_path} is empty. Starting with fresh history.")
                    self.messages = []
                    self.memory = deque(maxlen=30)
                    self.bookmarks = []
                else:
                    with open(self.chat_history_file_path, "r", encoding="utf-8") as f: history = json.load(f)
                    self.messages = history.get("messages", [])
                    self.memory = deque(history.get("memory", []), maxlen=30) # Restore memory
                    self.bookmarks = history.get("bookmarks", [])

                    # saved_dataset_path_str = history.get("analysis_file_path")
                    # if saved_dataset_path_str:
                    #     saved_dataset_path = Path(saved_dataset_path_str)
                    #     if saved_dataset_path.exists():
                    #         self.current_dataset_file_path = saved_dataset_path
                    #         self.current_dataset_display_name = self.current_dataset_file_path.name
                    #         self.current_input_data_type = history.get("input_data_type", self.current_input_data_type)
                    saved_dataset_path_str = history.get("analysis_file_path")
                    if saved_dataset_path_str:
                        saved_dataset_path = Path(saved_dataset_path_str)
                        if saved_dataset_path.exists():
                            # This now correctly sets the single 'source of truth' dictionary
                            self.current_dataset = {
                                "path": saved_dataset_path,
                                "display_name": saved_dataset_path.name,
                                "type": history.get("input_data_type", "csv")
                            }
                    
                    # if self.initial_dataset_path_from_arg and self.initial_dataset_path_from_arg.exists():
                    #     self.current_dataset_file_path = self.initial_dataset_path_from_arg
                    #     self.current_dataset_display_name = self.current_dataset_file_path.name
                    #     self.current_input_data_type = self.cli_args.input_data_type

                    if self.initial_dataset_path_from_arg and self.initial_dataset_path_from_arg.exists():
                        display_name = self.cli_args.file_name or self.initial_dataset_path_from_arg.name
                        self.current_dataset = {
                            "path": self.initial_dataset_path_from_arg,
                            "display_name": display_name,
                            "type": self.cli_args.input_data_type,
                        }

                    summary_path_str = history.get("summary_stats_csv_path"); eda_path_str = history.get("eda_report_path")
                    if summary_path_str and Path(summary_path_str).exists(): self.summary_stats_csv_path = Path(summary_path_str)
                    if eda_path_str and Path(eda_path_str).exists(): self.eda_report_path = Path(eda_path_str)
                    
                    bookmarked_message_timestamps = {bm.get('assistant_response', {}).get('timestamp') for bm in self.bookmarks if bm.get('assistant_response')}
                    for msg in self.messages:
                        if msg.get("role") == "assistant" and msg.get("timestamp") in bookmarked_message_timestamps:
                            msg['bookmarked'] = True
                        # if msg.get("role") == "assistant":
                        #     # any existing cost will be kept; missing ones default to None
                        #     msg.setdefault("cost", None) 
                
                logging.info(f"Chat history loaded from {self.chat_history_file_path}")
            except Exception as e: logging.error(f"Error loading chat history: {e}", exc_info=True)
        self.db_available = init_feedback_db()


    def save_chat_history(self):
        history = {
            "messages": self.messages, "memory": list(self.memory), # Save memory
            "bookmarks": self.bookmarks,
            "analysis_file_path": str(self.current_dataset_file_path) if self.current_dataset_file_path else None,
            "input_data_type": self.current_input_data_type,
            "summary_stats_csv_path": str(self.summary_stats_csv_path) if self.summary_stats_csv_path else None,
            "eda_report_path": str(self.eda_report_path) if self.eda_report_path else None,
        }
        try:
            with open(self.chat_history_file_path, "w", encoding="utf-8") as f: json.dump(history, f, indent=2)
            logging.info(f"Chat history (including memory and bookmarks) saved to {self.chat_history_file_path}.")
        except Exception as e: logging.error(f"Error saving chat history: {e}", exc_info=True)

    def _get_api_key_for_model(self):
        """Determines which API key to use based on the selected model provider."""
        if self.selected_model_id.startswith("groq/"):
            return self.groq_api_key
        # Default to OpenAI for "openai/" prefix or any other case
        return self.openai_api_key


    def try_initialize_agent(self):
        """Initializes or re-initializes the DSPy agent with enhanced error handling, using global logging."""
        status_message = "Agent: Unknown"
        status_color = 'grey'
        agent_outputs_dir = self.outputs_dir

        # Using global logging
        logging.info(f"Attempting to initialize DSPy agent with model: {self.selected_model_id}")

        # Get the appropriate API key
        final_api_key = self._get_api_key_for_model()
        dspy_model_id_for_config = self.selected_model_id

        if not dspy_model_id_for_config:
            self.dspy_agent = None
            status_message = "Agent Not Ready: No model selected. Please select a model in the sidebar."
            status_color = 'red'
            ui.notify(status_message, type='negative', multi_line=True, classes='w-96', auto_close=False, position='center')
            logging.error(status_message) # Using global logging
        elif not final_api_key:
            self.dspy_agent = None
            provider_name = "the selected provider"
            if dspy_model_id_for_config.startswith("openai/"):
                provider_name = "OpenAI"
            elif dspy_model_id_for_config.startswith("groq/"):
                provider_name = "Groq"
            status_message = f"Agent Not Ready: API Key for {provider_name} is missing. Please configure it in the sidebar."
            status_color = 'red'
            ui.notify(status_message, type='negative', multi_line=True, classes='w-96', auto_close=False, position='center')
            logging.error(status_message) # Using global logging
        else:
            logging.debug(f"API Key present for {dspy_model_id_for_config}. Proceeding with DSPy agent initialization.") # Using global logging
            try:
                logging.info("Compiling DSPy agent with provided API key and model ID...") # Using global logging
                self.dspy_agent = get_compiled_dspy_agent(
                    api_key=final_api_key,
                    model_id_with_prefix=dspy_model_id_for_config,
                    outputs_dir=agent_outputs_dir,
                    current_dataset_path=self.current_dataset_file_path,
                    examples_file_path=self.dspy_examples_file,
                    compile_agent=self.compile_dspy_agent_on_startup
                )
                
                if not self.dspy_agent: 
                    raise RuntimeError("DSPy agent initialization returned None unexpectedly.")

                status_message = f"Agent Ready ({self.selected_model_name})"
                status_color = 'green'
                
                if self.compile_dspy_agent_on_startup and not load_examples_from_json(self.dspy_examples_file):
                    status_message += " (Uncompiled - No Examples)"
                    status_color = 'orange'
                elif not self.compile_dspy_agent_on_startup:
                    status_message += " (Uncompiled - By Setting)"
                    status_color = 'orange'
                
                ui.notify(status_message, type='positive' if status_color == 'green' else 'warning', timeout=3500, position='top')
                logging.info(status_message) # Using global logging

            except Exception as e:
                self.dspy_agent = None
                # Using global logging
                logging.error(f"DSPy Agent initialization/compilation failed for model '{dspy_model_id_for_config}': {e}", exc_info=True) 
                
                error_str = str(e).lower()
                auth_keywords = ["authentication", "api key", "invalid key", "permission denied", "unauthorized", "401"]
                model_not_found_keywords = ["model_not_found", "does not exist", "404", "no model", "could not find model"]
                connection_error_keywords = ["connection", "timeout", "refused", "dns resolution"]
                
                if any(k in error_str for k in auth_keywords):
                    status_message = f"Agent Error: API Key for {self.selected_model_name} seems invalid or lacks permissions."
                elif any(k in error_str for k in model_not_found_keywords):
                    status_message = f"Agent Error: Model '{self.selected_model_name}' not found or not accessible."
                elif any(k in error_str for k in connection_error_keywords):
                    status_message = f"Agent Error: Network issue connecting to {self.selected_model_name} provider. Check connection/VPN."
                elif "rate limit" in error_str:
                    status_message = f"Agent Error: Rate limit exceeded for {self.selected_model_name}. Please try again later."
                else:
                    status_message = f"Agent Error: Failed to initialize {self.selected_model_name}. Check server console for details."
                
                status_color = 'red'
                detailed_error_msg = f"{status_message} Details: {str(e)[:150]}..."
                ui.notify(detailed_error_msg, type='negative', multi_line=True, classes='w-96 whitespace-pre-wrap', auto_close=False, position='center', close_button='OK')
                logging.error(detailed_error_msg) # Using global logging

        if self.sidebar_api_status_label:
            self.sidebar_api_status_label.set_text(status_message)
            self.sidebar_api_status_label.style(f'color: {status_color}; font-weight: bold; font-size: 0.8rem;')
            self.sidebar_api_status_label.tooltip(status_message if len(status_message) > 40 else '')
        
        return self.dspy_agent is not None


    async def handle_user_input(self, user_question: str | None):
        if not user_question or not user_question.strip():
            ui.notify("Please enter a question.", type='warning')
            if self.chat_input_field: self.chat_input_field.set_value(None)
            return
        
        if self.chat_input_field: self.chat_input_field.set_value(None)

        is_load_command = any(keyword in user_question.lower() for keyword in ["load", "upload", "dataset", "file", "open", "use"])
        if not self.current_dataset_file_path and not is_load_command :
            ui.notify("Please upload or specify a dataset first, or ask to load one.", type='warning', position='center')
            return

        if not self.dspy_agent:
            self.try_initialize_agent() # Attempt to initialize if not already
            if not self.dspy_agent:
                ui.notify("Agent not initialized. Please check API keys and model selection in the sidebar.", type='error', position='center', auto_close=False)
                return
        
        self.messages.append({
            "role": "user", 
            "content": user_question, 
            "type": "text", 
            "timestamp": pd.Timestamp.now(tz='UTC').isoformat()
        })
        self.memory.append(f"User: {user_question}") # Add to conversation memory
        self.update_chat_display()

        spinner_row_to_delete = None
        if self.chat_container:
            with self.chat_container:
                with ui.row().classes('w-full justify-center my-2') as temp_spinner_row:
                    ui.spinner(size='lg', color='primary')
                spinner_row_to_delete = temp_spinner_row
        
        parsed_response_dict = {"explanation": "Error processing request.", "plots": [], "files": [], "next_steps_suggestion": []}
        formatted_middle_steps = "*Agent did not provide detailed steps or an error occurred during generation.*"
        prediction = None 
        trajectory_data = None
        total_cost = None

        try:
            # Construct context for DSPy agent
            memory_history_str = "\n".join(list(self.memory)[-10:]) # Use last 5 user/assistant exchanges for context
            dataset_info_str = "No dataset currently loaded."
            if self.current_dataset_file_path:
                dataset_info_str = (
                    # f"Current dataset path for tool: '{self.current_dataset_file_path}'.\n"
                    # f"Dataset type: '{self.current_input_data_type}'.\n"
                    f"Current dataset path for tool: '{self.current_dataset['path']}'.\n"
                    f"Dataset type: '{self.current_dataset['type']}'.\n"
                    f"Agent's output directory for saving files: '{self.outputs_dir}'. "
                    f"Tool must save generated files (plots, CSVs) into 'outputs_dir / \"{AGENT_GENERATED_FILES_SUBDIR.name}\"/' "
                    f"(e.g., outputs_dir / \"{AGENT_GENERATED_FILES_SUBDIR.name}/plot.png\").\n"
                    f"Code MUST print the relative path from '{self.outputs_dir}' for any saved file (e.g., print 'generated_file/my_plot.png')."
                )

            agent_context = (
                f"CONVERSATION HISTORY (last few exchanges):\n{memory_history_str}\n\n"
                f"DATASET INFORMATION:\n{dataset_info_str}\n\n"
                f"PYTHON TOOL ('python_code_executor') INFORMATION:\n"
                f"- Input: 'code' (a string of Python code to execute).\n"
                f"- Output: STDOUT and any errors from execution.\n"
                f"- Environment: The code will have 'outputs_dir' (a Path object to '{self.outputs_dir}') "
                f"and 'dataset_path_in_tool_code' (a Path object to '{self.current_dataset_file_path}') available.\n"
                f"- Saving Files: The code MUST save any generated files (plots, CSVs) into the subdirectory "
                f"'{AGENT_GENERATED_FILES_SUBDIR.name}' within 'outputs_dir'. For example, a plot should be saved to "
                f"'outputs_dir / \"{AGENT_GENERATED_FILES_SUBDIR.name}\" / \"my_plot.png\"'.\n"
                f"- Outputting Paths: For any file saved, the code MUST print its relative path from 'outputs_dir'. "
                f"For example: 'print(\"{AGENT_GENERATED_FILES_SUBDIR.name}/my_plot.png\")'. This is crucial for the UI to find the files."
            )
            
            logging.info(f"Context for DSPy agent (first 300 chars): {agent_context[:300]}...")
            
            # Update the PythonCodeTool instance with the current dataset path for this run
            if self.dspy_agent and hasattr(self.dspy_agent, 'react_agent') and self.dspy_agent.react_agent.tools:
                for tool_instance in self.dspy_agent.react_agent.tools:
                    if isinstance(tool_instance, PythonCodeTool):
                        tool_instance.current_dataset_path = self.current_dataset_file_path
                        tool_instance.outputs_dir = self.outputs_dir # Also ensure outputs_dir is current
                        logging.info(f"Updated PythonCodeTool with dataset: {self.current_dataset_file_path} and outputs_dir: {self.outputs_dir}")
                        break
            
            # Run the DSPy agent in a separate thread
            with dspy.context():
                prediction = await asyncio.to_thread(
                    self.dspy_agent, question=user_question, context=agent_context
                )
            
            # usage_data = prediction.get_lm_usage()
            # logging.info(f"Retrieved usage directly from LM: {usage_data}")
            # logging.info(f"before usage,DSPy agent prediction received: {prediction}")
            # if usage_data:
            #     logging.info(f"uage:{usage_data}")
            #     pricing = MODEL_PRICING.get(self.selected_model_id, {})
            #     prompt_cost     = usage_data.prompt_tokens     * pricing.get("prompt", 0)
            #     completion_cost = usage_data.completion_tokens * pricing.get("completion", 0)
            #     total_cost = prompt_cost + completion_cost

            # logging.info("Calculating cost by manually aggregating from lm.history...")
            # total_prompt_tokens = 0
            # total_completion_tokens = 0
            # cost_calculated = False

            # # The history is on the configured language model object itself.
            # lm_history = dspy.settings.lm.history if hasattr(dspy.settings.lm, 'history') else []

            # if lm_history:
            #     for api_call in lm_history:
            #         # According to the documentation, 'usage' is a direct key in each history entry.
            #         usage_data = api_call.get('usage')
            #         if usage_data:
            #             prompt_tokens = usage_data.get("prompt_tokens", 0)
            #             completion_tokens = usage_data.get("completion_tokens", 0)
            #             total_prompt_tokens += prompt_tokens
            #             total_completion_tokens += completion_tokens

            #     if total_prompt_tokens > 0 or total_completion_tokens > 0:
            #         pricing = MODEL_PRICING.get(self.selected_model_id, {})
            #         prompt_cost = total_prompt_tokens * pricing.get("prompt", 0)
            #         completion_cost = total_completion_tokens * pricing.get("completion", 0)
            #         total_cost = prompt_cost + completion_cost
            #         logging.info(
            #             f"SUCCESS: Final cost is ${total_cost:.6f} from "
            #             f"({total_prompt_tokens} prompt + {total_completion_tokens} completion tokens)"
            #         )
            #         cost_calculated = True

            # if not cost_calculated:
            #     logging.error("FAILURE: No usage data was found in any lm.history entries after the call.")

            
            # --- Enhanced Debugging for Prediction and Trajectory ---
            logging.info(f"--- Prediction Object Start ---")
            logging.info(f"Type of prediction: {type(prediction)}")
            if prediction is not None:
                # logging.info(f"Prediction object dir(): {dir(prediction)}")
                # try:
                #     if hasattr(prediction, '__dict__'):
                #         logging.info(f"Prediction object vars(): {vars(prediction)}")
                #     else:
                #         logging.info(f"Prediction raw content: {str(prediction)[:1000]}")
                # except TypeError:
                #     logging.info(f"Prediction raw content (vars() failed): {str(prediction)[:1000]}")

                if hasattr(prediction, 'trajectory') and prediction.trajectory:
                    logging.info(f"Found prediction.trajectory. Type: {type(prediction.trajectory)}. Length: {len(prediction.trajectory) if isinstance(prediction.trajectory, list) else 'N/A'}")
                    logging.info(f"Prediction.trajectory content: {prediction.trajectory}")
                    trajectory_data = prediction.trajectory
                elif hasattr(prediction, 'rationale') and prediction.rationale:
                    logging.info(f"Found prediction.rationale: {prediction.rationale}")
                    trajectory_data = prediction.rationale
                else:
                    logging.warning("Neither .trajectory nor .rationale found on prediction object. Checking LLM history as a fallback.")
                    # Fallback: Inspect the last LLM interaction if direct trajectory is missing
                    # This is less ideal for ReAct but can give some clues.
                    if dspy.settings.lm and hasattr(dspy.settings.lm, 'history') and dspy.settings.lm.history:
                        logging.info(f"Attempting to use dspy.settings.lm.history. Length: {len(dspy.settings.lm.history)}")
                        # The history contains more raw request/response pairs.
                        # For ReAct, the 'trajectory' attribute is preferred.
                        # This is a simplification; parsing full history is complex.
                        # We'll pass it to format_raw_middle_steps_for_display which can try to make sense of it.
                        trajectory_data = dspy.settings.lm.history[-1] if dspy.settings.lm.history else None # Get the very last interaction
                        if trajectory_data: logging.info(f"Using last item from dspy.settings.lm.history: {trajectory_data}")


                # Uncomment to print detailed LLM history to console during debugging
                # logging.info("--- Full DSPy History (last 3 interactions) ---")
                # dspy.inspect_history(n=3, disabled=False) 
                # logging.info("--- End DSPy History ---")
            else:
                logging.error("Prediction object from agent is None.")
                trajectory_data = None
            # --- End Enhanced Debugging ---

            formatted_middle_steps = self.format_raw_middle_steps_for_display(trajectory_data)
            
            if prediction and hasattr(prediction, 'answer') and prediction.answer:
                parsed_response_dict = self.parse_response_content_for_nicegui(prediction.answer)
            elif prediction: # If no answer but prediction exists
                logging.warning("Prediction object does not have 'answer' attribute or it's empty. Using str(prediction) as explanation.")
                # The prediction itself might be the string output if the signature wasn't fully adhered to
                parsed_response_dict = self.parse_response_content_for_nicegui(str(prediction))
            else: # Prediction is None or no useful content
                parsed_response_dict = {"explanation": "Agent did not return a valid response.", "plots": [], "files": [], "next_steps_suggestion": []}
                logging.error("Agent did not return a usable response (prediction is None or lacks answer).")

        except Exception as e:
            logging.error(f"Error during DSPy agent interaction for '{user_question}': {e}", exc_info=True)
            parsed_response_dict = {"explanation": f"An internal error occurred while processing your request: {str(e)}", "plots": [], "files": [], "next_steps_suggestion": []}
            if not formatted_middle_steps or formatted_middle_steps.startswith("*Agent did not"):
                formatted_middle_steps = f"*Error during agent execution: {str(e)}*"
        finally:
            if spinner_row_to_delete:
                spinner_row_to_delete.delete()
        
        # --- Path handling for plots and files ---
        def make_ui_path(p_str, outputs_dir_base: Path, agent_subdir: Path):
            if not isinstance(p_str, str) or not p_str.strip():
                return None
            path_obj = Path(p_str)
            
            # Case 1: Agent returns an absolute path (should not happen if instructed otherwise)
            if path_obj.is_absolute():
                try:
                    # Try to make it relative to the main output directory
                    rel_path = path_obj.relative_to(outputs_dir_base)
                    logging.warning(f"Agent returned absolute path '{p_str}', converted to relative '{rel_path}'")
                    return str(rel_path)
                except ValueError:
                    logging.error(f"Agent returned absolute path '{p_str}' outside of outputs_dir '{outputs_dir_base}'. Cannot process.")
                    return None # Or handle as error

            # Case 2: Agent returns path already relative to AGENT_GENERATED_FILES_SUBDIR (e.g., "generated_file/plot.png")
            if path_obj.parts and path_obj.parts[0] == agent_subdir.name:
                return str(path_obj) # Already correct format

            # Case 3: Agent returns path relative to outputs_dir but *not* in AGENT_GENERATED_FILES_SUBDIR (e.g., "plot.png")
            # We expect it to be inside AGENT_GENERATED_FILES_SUBDIR as per tool description.
            # If it's just a filename, assume it *should* be in the agent's subdir.
            if len(path_obj.parts) == 1: # Just a filename like "plot.png"
                # Prepend the agent's subdirectory
                return str(agent_subdir / path_obj.name)
            
            # Case 4: Agent returns a path like "subdir_within_generated_file/plot.png"
            # This is fine if AGENT_GENERATED_FILES_SUBDIR is the root for such paths.
            # For simplicity, we assume agent places files directly in AGENT_GENERATED_FILES_SUBDIR
            # or prints paths relative to it.

            logging.warning(f"Path '{p_str}' from agent has unexpected format. Assuming it's relative to '{agent_subdir}'.")
            return str(agent_subdir / path_obj) # Fallback assumption

        assistant_plots_raw = parsed_response_dict.get("plots", [])
        assistant_files_raw = parsed_response_dict.get("files", [])

        assistant_plots = [make_ui_path(p, self.outputs_dir, AGENT_GENERATED_FILES_SUBDIR) for p in assistant_plots_raw if p]
        assistant_plots = [p for p in assistant_plots if p] # Filter out Nones

        assistant_files = [make_ui_path(f, self.outputs_dir, AGENT_GENERATED_FILES_SUBDIR) for f in assistant_files_raw if f]
        assistant_files = [f for f in assistant_files if f] # Filter out Nones
        # --- End Path handling ---

        assistant_message = {
            "role": "assistant", 
            "timestamp": pd.Timestamp.now(tz='UTC').isoformat(),
            "content": parsed_response_dict.get("explanation", "No explanation provided."),
            "plots": assistant_plots, 
            "files": assistant_files,
            "middle_steps": formatted_middle_steps,
            "type": "text_with_attachments",
            "next_steps": parsed_response_dict.get("next_steps_suggestion", []),
            # "cost": total_cost, 
        }
        self.messages.append(assistant_message)
        self.memory.append(f"Assistant: {str(assistant_message['content'])[:200]}...") 
        
        self.update_chat_display()
        self.save_chat_history()

        new_assistant_message_idx = len(self.messages) - 1
        if assistant_message.get("plots") or assistant_message.get("files") or \
           (assistant_message.get("middle_steps") and not str(assistant_message.get("middle_steps", "")).startswith("*")):
            self.show_details_for_message(new_assistant_message_idx)

    def parse_response_content_for_nicegui(self, final_answer_json_str: str | dict ):
        """Parses the JSON string from DSPy agent's answer field."""
        if isinstance(final_answer_json_str, dict): # Already a dict
            # Ensure standard keys
            return {
                "explanation": final_answer_json_str.get("explanation", "No explanation provided."),
                "plots": final_answer_json_str.get("plots", []),
                "files": final_answer_json_str.get("files", []),
                "next_steps_suggestion": final_answer_json_str.get("next_steps_suggestion", [])
            }
        
        if not isinstance(final_answer_json_str, str):
            logging.warning(f"DSPy final_answer not a string or dict: {type(final_answer_json_str)}. Content: {str(final_answer_json_str)[:200]}")
            return {"explanation": f"Unexpected response format: {str(final_answer_json_str)[:100]}", "plots": [], "files": [], "next_steps_suggestion": []}
        
        try:
            # The final_answer from DSPy Signature is expected to be a well-formed JSON string.
            # Sometimes, LLMs might wrap it in ```json ... ``` or add preamble/postamble.
            # A robust way is to extract the first valid JSON object.
            match = re.search(r"\{.*\}", final_answer_json_str, re.DOTALL)
            if match:
                json_str_to_parse = match.group(0)
            else:
                json_str_to_parse = final_answer_json_str # Assume it's already a plain JSON string

            parsed = json.loads(json_str_to_parse)
            
            # Validate structure
            if not isinstance(parsed.get("explanation"), (str, list)): # Allow list for multi-line explanations
                 logging.warning(f"Parsed JSON from DSPy has unexpected 'explanation' type: {type(parsed.get('explanation'))}")
                 parsed["explanation"] = str(parsed.get("explanation", "Agent provided an explanation in an unexpected format."))
            if isinstance(parsed.get("explanation"), list): # Join list to string if needed by UI
                 parsed["explanation"] = "\n".join(parsed["explanation"])

            if not isinstance(parsed.get("plots"), list):
                 logging.warning(f"Parsed JSON from DSPy has unexpected 'plots' type: {type(parsed.get('plots'))}")
                 parsed["plots"] = []
            if not isinstance(parsed.get("files"), list):
                 logging.warning(f"Parsed JSON from DSPy has unexpected 'files' type: {type(parsed.get('files'))}")
                 parsed["files"] = []
            if not isinstance(parsed.get("next_steps_suggestion"), list):
                 parsed["next_steps_suggestion"] = []


            return parsed
        except json.JSONDecodeError as e:
            logging.error(f"Error parsing DSPy agent's final_answer JSON: {e}. Content: {final_answer_json_str[:500]}", exc_info=True)
            return {"explanation": f"Could not parse LLM's structured response. Raw content: {final_answer_json_str[:200]}", "plots": [], "files": [], "next_steps_suggestion": []}
        except Exception as e_gen:
            logging.error(f"Generic error parsing DSPy agent's response: {e_gen}. Content: {final_answer_json_str[:500]}", exc_info=True)
            return {"explanation": f"Error processing LLM response. Raw content: {final_answer_json_str[:200]}", "plots": [], "files": [], "next_steps_suggestion": []}


    def format_raw_middle_steps_for_display(self, trajectory_data) -> str:
        if not trajectory_data:
            return "*No detailed intermediate steps retrieved or trajectory_data is empty.*"

        if isinstance(trajectory_data, str):
            return f"#### Agent's Reasoning Log\n```text\n{trajectory_data}\n```"

        # Handle the new dictionary-based trajectory from ReAct
        if isinstance(trajectory_data, dict):
            logging.info(f"Formatting dictionary-based trajectory: {trajectory_data.keys()}")
            formatted_steps_md_parts = ["#### Agent's Workings (Thought, Action, Observation)\n"]
            
            # Assuming steps are indexed like thought_0, tool_name_0, tool_args_0, observation_0
            # We need to find the maximum index for steps
            max_idx = -1
            for key in trajectory_data.keys():
                if key.startswith('thought_') or key.startswith('tool_name_') or key.startswith('tool_args_') or key.startswith('observation_'):
                    try:
                        idx = int(key.split('_')[-1])
                        if idx > max_idx:
                            max_idx = idx
                    except ValueError:
                        continue
            
            if max_idx == -1 and 'thought' in trajectory_data: # Simpler, non-indexed ReAct output
                 current_step_md_parts = [f"\n##### Step 1"]
                 thought_content = trajectory_data.get("thought")
                 action_name = trajectory_data.get("action") # Or tool_name
                 action_input_dict = trajectory_data.get("action_input") # Or tool_args
                 observation = trajectory_data.get("observation", trajectory_data.get("tool_output"))

                 if thought_content:
                     current_step_md_parts.append(f"**Thought:**\n```text\n{str(thought_content).strip()}\n```")
                 
                 if action_name and action_input_dict is not None:
                     action_input_str_parts = []
                     if isinstance(action_input_dict, dict):
                         for key, value in action_input_dict.items():
                             lang = 'python' if key == "code" else 'text'
                             action_input_str_parts.append(f"**Tool Input ({key}):**\n```{lang}\n{str(value).strip()}\n```")
                     else:
                          action_input_str_parts.append(f"**Tool Input:**\n```text\n{str(action_input_dict).strip()}\n```")
                     current_step_md_parts.append(f"**Action Called:** `{action_name}`\n" + "\n".join(action_input_str_parts))
                 elif action_name:
                     current_step_md_parts.append(f"**Action Called:** `{action_name}` (No detailed input logged)")

                 if observation is not None:
                     obs_str = str(observation)
                     obs_str = (obs_str[:1500] + "\n... (observation truncated)") if len(obs_str) > 1500 else obs_str
                     current_step_md_parts.append(f"**Observation/Tool Output:**\n```text\n{obs_str.strip()}\n```")
                 
                 if len(current_step_md_parts) > 1:
                     formatted_steps_md_parts.append("\n\n".join(current_step_md_parts))

            else: # Indexed steps
                for i in range(max_idx + 1):

                    is_last_step = (i == max_idx)
                    observation_for_check = str(trajectory_data.get(f'observation_{i}') or trajectory_data.get(f'tool_output_{i}', ''))
                    is_failed_step = "is not in the tool's args" in observation_for_check or "Execution error in finish" in observation_for_check


                    current_step_md_parts = [f"\n##### Step {i + 1}"]
                    thought_content = trajectory_data.get(f'thought_{i}') or trajectory_data.get(f'rationale_{i}')
                    action_name = trajectory_data.get(f'tool_name_{i}') or trajectory_data.get(f'action_{i}')
                    action_input_dict = trajectory_data.get(f'tool_args_{i}') or trajectory_data.get(f'action_input_{i}')
                    observation = trajectory_data.get(f'observation_{i}') or trajectory_data.get(f'tool_output_{i}')
                    
                    if is_last_step and is_failed_step:
                        observation = None # Don't show observation for failed last step, it might be an error message

                    if thought_content:
                        current_step_md_parts.append(f"**Thought:**\n```text\n{str(thought_content).strip()}\n```")
                    
                    if action_name and action_input_dict is not None:
                        action_input_str_parts = []
                        if isinstance(action_input_dict, dict):
                            for key, value in action_input_dict.items():
                                lang = 'python' if key == "code" else 'text'
                                action_input_str_parts.append(f"**Tool Input ({key}):**\n```{lang}\n{str(value).strip()}\n```")
                        else: # If action_input_dict is a string (e.g. for some tools)
                            action_input_str_parts.append(f"**Tool Input:**\n```text\n{str(action_input_dict).strip()}\n```")
                        current_step_md_parts.append(f"**Action Called:** `{action_name}`\n" + "\n".join(action_input_str_parts))
                    elif action_name:
                         current_step_md_parts.append(f"**Action Called:** `{action_name}` (No detailed input logged)")

                    if observation is not None:
                        obs_str = str(observation)
                        obs_str = (obs_str[:1500] + "\n... (observation truncated)") if len(obs_str) > 1500 else obs_str
                        current_step_md_parts.append(f"**Observation/Tool Output:**\n```text\n{obs_str.strip()}\n```")
                    
                    if len(current_step_md_parts) > 1:
                        formatted_steps_md_parts.append("\n\n".join(current_step_md_parts))

            return "\n\n---\n".join(formatted_steps_md_parts) if len(formatted_steps_md_parts) > 1 else "*No processable steps found in trajectory dictionary.*"

        # Fallback for other types or if the list format is still expected for some cases
        if isinstance(trajectory_data, list) and trajectory_data:
            # This is just a placeholder to show where it would go.
            logging.info("Processing trajectory_data as a list.")
            return "*List-based trajectory processing not fully shown here, adapt as needed.*"


        logging.warning(f"Trajectory data in unexpected format. Type: {type(trajectory_data)}. Content: {str(trajectory_data)[:500]}")
        return f"*Trajectory data in unexpected format. Please check server logs for details. Type: {type(trajectory_data)}*"


    async def on_page_load_actions(self, client: Client):
        logging.info(f"Client connected (User: {self.user_id}). Loading initial actions.")
        dataset_loaded = False
        # if self.initial_dataset_path_from_arg and self.initial_dataset_path_from_arg.exists():
        #     self.current_dataset_file_path = self.initial_dataset_path_from_arg
        #     self.current_dataset_display_name = self.current_dataset_file_path.name
        #     self.current_input_data_type = self.cli_args.input_data_type
        #     ui.notify(f"Loading dataset from arg: {self.current_dataset_display_name}", type='info', timeout=2000)
        #     await self.preview_loaded_or_uploaded_dataset()
        #     dataset_loaded = True
        # if self.initial_dataset_path_from_arg and self.initial_dataset_path_from_arg.exists():
        #     self.current_dataset_file_path = self.initial_dataset_path_from_arg
            
        #     # Apply the same logic here to check for the custom file_name
        #     if self.cli_args.file_name:
        #         self.current_dataset_display_name = self.cli_args.file_name
        #     else:
        #         self.current_dataset_display_name = self.current_dataset_file_path.name

        #     self.current_input_data_type = self.cli_args.input_data_type

        if self.initial_dataset_path_from_arg and self.initial_dataset_path_from_arg.exists():
            display_name = self.cli_args.file_name or self.initial_dataset_path_from_arg.name
            self.current_dataset = {
                "path": self.initial_dataset_path_from_arg,
                "display_name": display_name,
                "type": self.cli_args.input_data_type,
            }
            ui.notify(f"Loading dataset from arg: {self.current_dataset_display_name}", type='info', timeout=2000)
            await self.preview_loaded_or_uploaded_dataset()
            dataset_loaded = True
        elif self.current_dataset_file_path and self.current_dataset_file_path.exists():
            ui.notify(f"Restoring session with: {self.current_dataset_display_name}", type='info', timeout=2000)
            await self.preview_loaded_or_uploaded_dataset()
            dataset_loaded = True
        
        if not dataset_loaded and self.dataset_preview_area:
            self.dataset_preview_area.clear()
            with self.dataset_preview_area: ui.label("Upload dataset or provide via CLI to start.").classes("text-gray-500 m-2")

        self.update_chat_display()
        self.update_details_pane() # Ensure this handles new middle_steps format
        self.update_sidebar_bookmarks()
        self.try_initialize_agent() # Initialize DSPy agent

    def on_page_unload_actions(self, client: Client):
        logging.info(f"Client disconnected (User: {self.user_id}). Saving history.")
        self.save_chat_history()

    def handle_model_change(self, e):
        self.selected_model_id = e.value
        self.selected_model_name = self.MODEL_OPTIONS_SELECT.get(self.selected_model_id, self.selected_model_id)
        ui.notify(f"Model set to: {self.selected_model_name}", type='info', position='top-right', timeout=2000)
        self.try_initialize_agent() # Re-initialize/re-compile agent

    def save_openai_key(self):
        if self.openai_key_input:
            self.openai_api_key = self.openai_key_input.value or ""
            save_key_to_specific_file(OPENAI_API_KEY_FILE, self.openai_api_key)
            ui.notify("OpenAI Key " + ("saved." if self.openai_api_key else "cleared."), type='positive' if self.openai_api_key else 'info')
            self.try_initialize_agent()

    def save_groq_key(self):
        if self.groq_key_input:
            self.groq_api_key = self.groq_key_input.value or ""
            save_key_to_specific_file(GROQ_API_KEY_FILE, self.groq_api_key)
            ui.notify("Groq Key " + ("saved." if self.groq_api_key else "cleared."), type='positive' if self.groq_api_key else 'info')
            self.try_initialize_agent()

    async def run_eda_action(self):
        if not self.current_dataset_file_path:
            ui.notify("Dataset not ready for EDA. Please upload a dataset.", type='warning'); return
        if not self.dspy_agent:
            ui.notify("Agent not ready for EDA. Please check configuration.", type='warning'); return

        eda_user_query = (
            "Perform a comprehensive Exploratory Data Analysis (EDA) on the current dataset. "
            "Include: summary statistics, missing value analysis, data type identification, "
            "a correlation matrix (with heatmap visualization), distributions for numerical features, "
            "and counts for categorical-like features. "
            "Conclude with 3-5 key insights derived from this analysis. "
        )
        ui.notify("Starting Comprehensive EDA...", type='info')
        await self.handle_user_input(eda_user_query)


    def build_ui(self):
        ui.add_head_html("""
            <style>
                .link-styling a { color: #3f51b5; text-decoration: underline; } .link-styling a:hover { color: #283593; }
                .middle-steps-content { font-size: 0.75rem; max-height: 500px; overflow-y: auto; background-color: #f9f9f9; border: 1px solid #e0e0e0; padding: 8px; border-radius: 4px; }
                .middle-steps-content pre { white-space: pre-wrap !important; word-break: break-all; overflow-x: auto; background-color: #f0f4f8; padding: 0.5rem; border-radius: 0.25rem; border: 1px solid #e2e8f0; font-family: monospace; }
                .middle-steps-content code { font-family: monospace; }
                .custom-timestamp-style { font-size: 0.75em; color: #757575; margin-top: 4px; line-height: 1; width: 100%; text-align: right; padding-right: 8px; }
            </style>
        """)
        self.left_drawer = ui.left_drawer(elevated=True, top_corner=True, bottom_corner=True)\
            .props('overlay breakpoint=lg').style('background-color: #f4f6f8;')\
            .classes('p-4 w-80 lg:w-96 border-r')
        
        with ui.header(elevated=True).style('background-color: #303f9f;').classes('items-center text-white q-px-md'):
            if self.left_drawer: 
                ui.button(icon='menu', on_click=self.left_drawer.toggle).props('flat round color=white')
            ui.label("Galaxy Chat Analysis").classes("text-xl md:text-2xl font-semibold tracking-wide")
            
        with self.left_drawer:
            with ui.row().classes("w-full items-center justify-between no-wrap mb-2"):
                ui.label("Configuration").classes("text-lg font-semibold text-indigo-800")
                ui.button(icon='close', on_click=lambda: setattr(self.left_drawer, 'value', False)) \
                    .props('flat round dense color=grey-7').tooltip("Close Sidebar")
            
            self.sidebar_api_status_label = ui.label("Agent: Unknown").classes("mb-3 text-xs p-1 rounded")

            self.model_select_element = ui.select(
                self.MODEL_OPTIONS_SELECT,      # dict of value→label
                label='LLM Model',
                value=self.selected_model_id,
                on_change=self.handle_model_change
            ).props('outlined dense') \
            .classes('w-full mb-3')


            with ui.expansion("API Keys", icon="key", value=False).classes("w-full mb-3 text-sm"):
                self.openai_key_input = ui.input(label="OpenAI API Key", password=True, value=self.openai_api_key, on_change=lambda e: setattr(self, 'openai_api_key', e.value)).props("dense outlined clearable")
                ui.button("Save OpenAI", on_click=self.save_openai_key, icon="save").classes("w-full mt-1").props("color=indigo-6 dense size=sm")
                self.groq_key_input = ui.input(label="Groq API Key", password=True, value=self.groq_api_key, on_change=lambda e: setattr(self, 'groq_api_key', e.value)).props("dense outlined clearable mt-2")
                ui.button("Save Groq", on_click=self.save_groq_key, icon="save").classes("w-full mt-1").props("color=indigo-6 dense size=sm")

            ui.separator().classes("my-3")
            ui.label("Dataset").classes("text-md font-semibold mb-2 text-indigo-700")
            ui.upload(label="Upload New Dataset", auto_upload=True, on_upload=self.handle_upload, max_file_size=200 * 1024 * 1024).props("accept=.csv,.tsv,.h5ad,.xlsx,.xls,.json,.parquet,.h5,.fa,.fasta,.vcf,.gtf,.gff,.bed").classes("w-full mb-3")

            ui.label("Analysis Actions").classes("text-md font-semibold mt-3 mb-2 text-indigo-700")
            ui.button("Run Full EDA", on_click=self.run_eda_action, icon="query_stats").classes("w-full mb-1").props("color=deep-purple-6 dense")
            ui.separator().classes("my-3")

            with ui.expansion("⭐ Bookmarks", icon="bookmarks", value=True).classes("w-full text-sm"):
                self.bookmarks_container = ui.column().classes("w-full max-h-96 overflow-y-auto gap-1") 
                self.update_sidebar_bookmarks() # Initial population

        # Main layout with splitter
        with ui.splitter(value=65, reverse=False, limits=(40,70)).classes('w-full h-[calc(100vh-110px)] no-wrap overflow-hidden') as main_splitter:
            with main_splitter.before: # Chat panel
                with ui.column().classes("w-full h-full p-0 flex flex-col no-wrap items-stretch overflow-hidden min-h-0"):
                    self.chat_container = ui.column().classes("w-full flex-grow overflow-y-auto p-2 md:p-3 bg-gray-100 min-h-0") # Chat messages
                    
                    # with ui.row().classes("w-full px-2 pt-2 bg-slate-200 items-center border-t flex-shrink-0"): # Input row
                    #     self.chat_input_field = ui.input(placeholder="Ask about the dataset...")\
                    #         .props("bg-color=white outlined dense clearable rounded").classes("flex-grow")\
                    #         .on('keydown.enter', lambda: self.handle_user_input(self.chat_input_field.value), throttle=0.5)
                    #     ui.button(icon="send", on_click=lambda: self.handle_user_input(self.chat_input_field.value))\
                    #         .props("round color=indigo-6 dense unelevated")
                    
                    # ui.label("Outputs may require verification.") \
                    #     .classes("w-full text-xs text-gray-600 px-1 pb-1 text-center bg-slate-100 border-t flex-shrink-0")
                    with ui.column().classes("w-full p-2 bg-slate-200 border-t flex-shrink-0 gap-0"):

                       # First item in the column: a row for the input and button
                       with ui.row().classes("w-full items-center no-wrap"):
                           self.chat_input_field = ui.input(placeholder="Ask about the dataset...")\
                               .props("bg-color=white outlined dense clearable rounded").classes("flex-grow")\
                               .on('keydown.enter', lambda: self.handle_user_input(self.chat_input_field.value), throttle=0.5)
                           ui.button(icon="send", on_click=lambda: self.handle_user_input(self.chat_input_field.value))\
                               .props("round color=indigo-6 dense unelevated")

                       # Second item in the column: the verification label, now inside the same container
                       ui.label("Outputs may require verification.") \
                           .classes("w-full text-xs text-gray-600 text-center pt-1")

            with main_splitter.after: # Details and Preview panel
                with ui.column().classes("w-full h-full items-stretch overflow-y-auto bg-slate-50 p-0"): 
                    ui.label("Details & Preview").classes("text-md font-semibold text-gray-700 sticky top-0 bg-slate-100/95 backdrop-blur-sm z-10 p-3 border-b shadow-sm")
                    with ui.column().classes("p-2 md:p-3 flex-grow w-full"):
                        self.details_container = ui.column().classes("w-full flex-grow p-2 border rounded-lg bg-white shadow mt-2 min-h-[200px]") 
                        self.dataset_preview_area = ui.column().classes("w-full mb-3 p-2 border rounded-lg bg-white shadow") 
                        
        
        # Keyboard listener for closing drawer
        ui.keyboard(self._handle_drawer_escape_key)

        app.on_connect(self.on_page_load_actions) 
        app.on_disconnect(self.on_page_unload_actions)


    async def handle_upload(self, e: UploadEventArguments):
        if not e.content: 
            ui.notify("No file content.", type='negative')
            return
        uploaded_filename = e.name
        # Determine file type - use suffix or allow user to specify later
        # self.current_input_data_type = Path(uploaded_filename).suffix.lower().replace('.', '')
        if not self.current_input_data_type: # Fallback if no suffix
            self.current_input_data_type = "csv" # Or ask user
            ui.notify(f"Could not determine file type for {uploaded_filename}, assuming CSV. You can change this if needed.", type='warning')

        # Save to outputs_dir/ (not AGENT_GENERATED_FILES_SUBDIR, as this is user upload)
        temp_file_path = self.outputs_dir / uploaded_filename 
        try:
            with open(temp_file_path, 'wb') as f:
                f.write(e.content.read())
            
            # self.current_dataset_file_path = temp_file_path
            # self.current_dataset_display_name = uploaded_filename

            self.current_dataset = {
                "path": temp_file_path,
                "display_name": uploaded_filename,
                "type": Path(uploaded_filename).suffix.lower().replace('.', '')
            }
            
            # Update PythonCodeTool's dataset path if agent is already initialized
            if self.dspy_agent and hasattr(self.dspy_agent, 'react_agent') and self.dspy_agent.react_agent.tools:
                for tool in self.dspy_agent.react_agent.tools:
                    if isinstance(tool, PythonCodeTool):
                        tool.current_dataset_path = self.current_dataset_file_path
                        logging.info(f"PythonCodeTool dataset path updated to: {self.current_dataset_file_path}")

            ui.notify(f"File '{uploaded_filename}' uploaded and set as current dataset.", type='positive')
            self.summary_stats_csv_path = None 
            self.eda_report_path = None
            
            self.messages.append({
                "role": "system", 
                "content": f"New dataset loaded: {uploaded_filename}. Its path is '{self.current_dataset_file_path}'. Type: '{self.current_input_data_type}'. Please analyze.", 
                "type": "text", 
                "timestamp": pd.Timestamp.now(tz='UTC').isoformat() 
            })
            self.update_chat_display()
            await self.preview_loaded_or_uploaded_dataset()
            self.save_chat_history()
        except Exception as ex:
            ui.notify(f"Error processing '{uploaded_filename}': {ex}", type='negative', multi_line=True)
            logging.error(f"Upload error for {uploaded_filename}: {ex}", exc_info=True)
            self.current_dataset_file_path = None
            self.current_dataset_display_name = "No dataset"
            await self.preview_loaded_or_uploaded_dataset() # Update preview to show no dataset

    def load_data_object_from_path(self, file_path: Path, data_type: str):
        try:
            if not file_path or not file_path.exists():
                logging.warning(f"File not found for loading: {file_path}")
                return None
            logging.info(f"Loading data from {file_path} as type {data_type}")
            if data_type == 'csv': return pd.read_csv(file_path)
            elif data_type == "tsv": return pd.read_csv(file_path, sep="\t")
            elif data_type == "h5ad": import anndata; return anndata.read_h5ad(file_path)
            elif data_type in ("xlsx", "xls"): return pd.read_excel(file_path)
            # ... (to-do: need include all other data type loaders) ...
            else: raise ValueError(f"Unsupported file type for direct load: {data_type}")
        except ImportError as ie: 
            ui.notify(f"Missing library for {data_type}: {ie}. Please install it.", type='error', multi_line=True, auto_close=False)
            logging.error(f"ImportError loading {file_path.name if file_path else 'N/A'} ({data_type}): {ie}", exc_info=True)
            return None
        except Exception as e: 
            ui.notify(f"Error loading {file_path.name if file_path else 'N/A'} ({data_type}): {e}", type='negative', multi_line=True, auto_close=False)
            logging.error(f"Load error for {file_path} ({data_type}): {e}", exc_info=True)
            return None

    async def preview_loaded_or_uploaded_dataset(self):
        # (This method should be largely the same, ensure it uses self.outputs_dir and AGENT_GENERATED_FILES_SUBDIR correctly for summary paths)
        if not self.current_dataset_file_path or not self.dataset_preview_area:
            if self.dataset_preview_area: 
                self.dataset_preview_area.clear()
                with self.dataset_preview_area: ui.label("No dataset selected or loaded.").classes("text-gray-500 m-2")
            self.current_data_object = None # Clear data object
            return

        self.dataset_preview_area.clear()
        with self.dataset_preview_area:
            # ui.label(f"Active: {self.current_dataset_display_name} ({self.current_input_data_type.upper()})").classes('text-md font-semibold mb-1')
            
            ui.label(f"Active: {self.current_dataset['display_name']} ({self.current_dataset['type'].upper()})").classes('text-md font-semibold mb-1')
            self.current_data_object = self.load_data_object_from_path(self.current_dataset_file_path, self.current_input_data_type)
            
            if self.current_data_object is None:
                ui.label("Failed to load data for preview. Check file type or content.").classes('text-red-500')
                return

            if isinstance(self.current_data_object, pd.DataFrame):
                ui.markdown("###### Data Preview (Top 5 Rows)"); 
                ui.table.from_pandas(self.current_data_object.head(5)).classes('h-[200px] max-h-[200px] overflow-auto w-full bordered').props('dense flat bordered separator=cell')
                
                # Generate summary if not already present or file missing
                summary_dir = self.outputs_dir / AGENT_GENERATED_FILES_SUBDIR
                summary_dir.mkdir(parents=True, exist_ok=True) # Ensure subdir for summaries exists
                expected_summary_filename_stem = f"summary_stats_for_{Path(self.current_dataset_display_name).stem}"
                # Search for existing summary rather than relying on exact UUID name
                existing_summaries = list(summary_dir.glob(f"{expected_summary_filename_stem}*.csv"))

                if existing_summaries and existing_summaries[0].exists():
                     self.summary_stats_csv_path = existing_summaries[0]
                elif not self.summary_stats_csv_path or not self.summary_stats_csv_path.exists():
                     self.summary_stats_csv_path = self.generate_and_save_pandas_summary_csv(self.current_data_object)

                if self.summary_stats_csv_path and self.summary_stats_csv_path.exists():
                    try:
                        summary_df = pd.read_csv(self.summary_stats_csv_path, index_col=0)
                        ui.markdown("###### Summary Statistics").classes('mt-2')
                        ui.table.from_pandas(summary_df).classes('h-[280px] max-h-[280px] overflow-auto w-full bordered').props('dense flat bordered separator=cell')
                        ui.button("Download Summary", icon="download", on_click=lambda: ui.download(str(self.summary_stats_csv_path), filename=self.summary_stats_csv_path.name)).props("dense size=sm flat").classes("mt-1 text-sm text-indigo-600 hover:text-indigo-800")
                    except Exception as e: 
                        ui.notify(f"Error displaying summary: {e}", type='warning')
                        logging.warning(f"Error displaying summary CSV from {self.summary_stats_csv_path}: {e}")
            # ... (add previews for other data types like anndata, fasta, vcf, gff) ...
            else:
                ui.label(f"Enhanced preview for {self.current_input_data_type.upper()} not fully shown here, but data object loaded.")

    def generate_and_save_pandas_summary_csv(self, dataframe: pd.DataFrame) -> Path | None:
        
        if not isinstance(dataframe, pd.DataFrame): return None
        original_filename_stem = Path(self.current_dataset_display_name).stem if self.current_dataset_display_name and self.current_dataset_display_name != "No dataset loaded" else "dataset"
        try:
            summary_df = dataframe.describe(include='all')
            summary_filename = f"summary_stats_for_{original_filename_stem}_{uuid.uuid4().hex[:6]}.csv"
            # Save summary stats into the agent's generated files subdirectory
            summary_csv_path = self.outputs_dir / AGENT_GENERATED_FILES_SUBDIR / summary_filename
            summary_csv_path.parent.mkdir(parents=True, exist_ok=True) # Ensure directory exists
            summary_df.to_csv(summary_csv_path, index=True)
            logging.info(f"Pandas summary saved: {summary_csv_path}")
            return summary_csv_path
        except Exception as e: 
            logging.error(f"Error generating/saving pandas summary: {e}", exc_info=True)
            ui.notify(f"Error in summary stats generation: {e}", type='negative')
            return None
            
    def update_sidebar_bookmarks(self):
        if not self.bookmarks_container: return
        self.bookmarks_container.clear()
        with self.bookmarks_container:
            if not self.bookmarks:
                ui.label("No bookmarks yet.").classes("text-xs text-gray-500 p-2 text-center")
            else:
                for idx, bookmark in enumerate(self.bookmarks):
                    user_q = bookmark.get("user_question", "Bookmarked Item")
                    assistant_resp = bookmark.get("assistant_response", {})
                    assistant_content_snippet = str(assistant_resp.get("content", ""))[:70] + "..."
                    with ui.card().tight().classes("w-full my-1 shadow-md hover:shadow-lg transition-shadow cursor-pointer"):
                        with ui.card_section().classes("p-2"):
                            with ui.row().classes("w-full items-center justify-between no-wrap"):
                                with ui.column().classes("flex-grow").on('click', lambda b=bookmark: self.show_bookmark_details(b)):
                                    ui.label(f"Q: {user_q[:50]}...").classes("text-xs font-semibold text-indigo-700").style("white-space: normal; word-break: break-word; line-height: 1.2;")
                                    ui.label(f"A: {assistant_content_snippet}").classes("text-xs text-gray-600 mt-1").style("white-space: normal; word-break: break-word; line-height: 1.2;")
                                ui.button(icon='delete_sweep', on_click=lambda i=idx: self.delete_bookmark(i), color='red-5') \
                                    .props('flat round dense size=xs').tooltip("Delete bookmark")


    def delete_bookmark(self, bookmark_idx: int):
        if 0 <= bookmark_idx < len(self.bookmarks):
            deleted_bookmark = self.bookmarks.pop(bookmark_idx)
            # Unmark original message
            deleted_timestamp = deleted_bookmark.get("assistant_response", {}).get("timestamp")
            if deleted_timestamp:
                for msg in self.messages:
                    if msg.get("role") == "assistant" and msg.get("timestamp") == deleted_timestamp:
                        msg.pop('bookmarked', None)
                        break
            ui.notify("Bookmark removed.", type='info')
            self.save_chat_history()
            self.update_sidebar_bookmarks()
            self.update_chat_display()
            if self.selected_bookmark_for_details and self.selected_bookmark_for_details.get("assistant_response", {}).get("timestamp") == deleted_timestamp:
                self.selected_bookmark_for_details = None
                self.update_details_pane()
        else:
            ui.notify("Could not delete bookmark (invalid index).", type='negative')


    def show_details_for_message(self, message_idx: int):
        self.selected_message_for_details_idx = message_idx
        self.selected_bookmark_for_details = None 
        if self.details_container:
            self.update_details_pane()
        else:
            logging.warning("Details container not initialized for message details.")

    def show_bookmark_details(self, bookmark_data: dict):
        self.selected_bookmark_for_details = bookmark_data
        self.selected_message_for_details_idx = None
        if self.details_container:
            self.update_details_pane()
        else:
            logging.warning("Details container not initialized for bookmark details.")
            
    def add_bookmark(self, message_idx: int):
        if 0 <= message_idx < len(self.messages) and self.messages[message_idx].get("role") == "assistant":
            assistant_msg = self.messages[message_idx]
            if assistant_msg.get('bookmarked'):
                ui.notify("This response is already bookmarked.", type='info'); return

            user_question = "Context not found"
            for i in range(message_idx - 1, -1, -1):
                if self.messages[i].get("role") == "user":
                    user_question = self.messages[i].get("content", "User query not found"); break
            
            bookmark_data = {
                "user_question": user_question,
                "assistant_response": {
                    "content": assistant_msg.get("content"),
                    "plots": assistant_msg.get("plots", []),
                    "files": assistant_msg.get("files", []),
                    "middle_steps": assistant_msg.get("middle_steps"), # Important for DSPy
                    "timestamp": assistant_msg.get("timestamp") 
                }
            }
            self.bookmarks.append(bookmark_data)
            self.messages[message_idx]['bookmarked'] = True
            ui.notify("Response bookmarked!", type='positive')
            self.save_chat_history()
            self.update_sidebar_bookmarks()
            self.update_chat_display()
        else:
            ui.notify("Could not bookmark this message.", type='negative')

    def update_details_pane(self):
        if not self.details_container:
            logging.warning("NiceGuiApp: Details container NA for update_details_pane.")
            return
        self.details_container.clear()

        source_data = None
        data_origin = None # 'live_message', 'bookmark', or 'live_message_default'

        # --- Logic to determine source_data and data_origin ---
        if self.selected_bookmark_for_details:
            source_data = self.selected_bookmark_for_details
            data_origin = 'bookmark'
        elif self.selected_message_for_details_idx is not None and \
             self.selected_message_for_details_idx < len(self.messages):
            source_data = self.messages[self.selected_message_for_details_idx]
            data_origin = 'live_message'
        elif self.selected_message_for_details_idx is None: # Default to last message with details
            for i in range(len(self.messages) - 1, -1, -1):
                msg = self.messages[i]
                if msg.get("role") == "assistant" and \
                   (msg.get("plots") or msg.get("files") or \
                    (msg.get("middle_steps") and not str(msg.get("middle_steps")).startswith("*No"))):
                    source_data = msg
                    data_origin = 'live_message_default'
                    break
        
        with self.details_container:
            if not source_data:
                ui.label("Select 'View Details' or a bookmark for details.").classes("text-gray-500 m-4 italic text-center")
                return

            # --- Initialize variables to hold content from source_data ---
            plots_raw = []
            files_raw = []
            middle_steps_content = None
            user_query_for_display = "N/A"
            assistant_content_for_display = "N/A" # For the main explanation

            if data_origin == 'live_message' or data_origin == 'live_message_default':
                msg_data = source_data
                ui.markdown("##### Agent Response Details")
                # Find associated user query
                current_idx = self.messages.index(msg_data) if msg_data in self.messages else -1
                if current_idx > 0:
                    for idx_q in range(current_idx - 1, -1, -1):
                        if self.messages[idx_q].get("role") == "user":
                            user_query_for_display = self.messages[idx_q].get("content", "N/A")
                            break
                
                assistant_content_for_display = msg_data.get("content", "No explanation provided.")
                plots_raw = msg_data.get("plots", [])
                files_raw = msg_data.get("files", [])
                middle_steps_content = msg_data.get("middle_steps")

            elif data_origin == 'bookmark':
                ui.markdown("##### Bookmarked Item Details")
                user_query_for_display = source_data.get("user_question", "N/A")
                assistant_resp = source_data.get("assistant_response", {})
                assistant_content_for_display = assistant_resp.get("content", "No explanation provided.")
                plots_raw = assistant_resp.get("plots", [])
                files_raw = assistant_resp.get("files", [])
                middle_steps_content = assistant_resp.get("middle_steps")

            # --- Display User Query and Assistant's Main Explanation ---
            if user_query_for_display != "N/A":
                ui.markdown("###### Regarding Query:").classes("text-gray-700 font-semibold mt-1 text-sm")
                ui.markdown(f"{user_query_for_display[:250]}{'...' if len(user_query_for_display)>250 else ''}").classes("text-gray-800 p-2 text-sm bg-slate-100 rounded-md border")

            # Display main explanation from assistant (if not already part of middle steps or other detailed views)
            # This assumes 'content' field holds the primary textual explanation.
            # if assistant_content_for_display != "N/A":
            #      ui.markdown("###### Agent's Explanation:").classes("text-gray-700 font-semibold mt-2 text-sm")
            #      ui.markdown(str(assistant_content_for_display)).classes("text-sm link-styling p-1") # Added p-1 for slight padding

            ui.separator().classes("my-3")

            # --- Display Middle Steps ---
            formatted_middle_steps_str = self.format_raw_middle_steps_for_display(middle_steps_content)
            if formatted_middle_steps_str and not formatted_middle_steps_str.startswith("*No"):
                with ui.expansion("Agent's Workings", icon="list_alt", value=True).classes("w-full my-2 border rounded shadow-sm"):
                    with ui.card_section().classes("bg-gray-50 p-2"): # Ensure card_section for proper styling
                        ui.markdown(formatted_middle_steps_str).classes('middle-steps-content') # Ensure .middle-steps-content CSS is defined
            elif middle_steps_content: 
                ui.markdown("###### Agent Workings (Raw/Fallback):").classes("mt-2 text-sm")
                ui.markdown(f"```text\n{str(middle_steps_content)[:1000]}\n```").classes("text-xs text-gray-600 bg-slate-50 p-2 border rounded")

            # --- Display Plots ---
            plots_to_display = [self.outputs_dir / p for p in plots_raw if p and isinstance(p, (str, Path)) and (self.outputs_dir / p).is_file()]
            if plots_to_display:
                ui.markdown("###### Plots").classes("mt-3 text-base font-medium text-gray-700") # Enhanced heading
                with ui.grid(columns=1).classes("gap-3 w-full"): # slightly more gap
                    for p_path in plots_to_display:
                        with ui.card().tight().classes("w-full shadow-md rounded-lg overflow-hidden"): # Added rounded-lg and overflow-hidden
                            try:
                                ui.image(str(p_path)).classes('max-w-full h-auto object-contain border-b') # border-b for separation
                                with ui.card_actions().props("align=right").classes("bg-slate-50 px-2 py-1"): # Actions with slight background
                                    ui.button(icon="download", on_click=lambda current_path=str(p_path): ui.download(current_path, filename=Path(current_path).name)) \
                                        .props("flat dense size=sm color=primary round").tooltip("Download Plot")
                            except Exception as e_img:
                                logging.error(f"Error displaying image {p_path}: {e_img}")
                                with ui.card_section().classes("p-2"):
                                     ui.label(f"Could not display plot: {p_path.name}").classes('text-red-500 text-xs')
            
            # --- Display Files (with corrected CSV table display) ---
            # files_to_display = [self.outputs_dir / f for f in files_raw if f and isinstance(f, (str, Path)) and (self.outputs_dir / f).is_file()]
            # if files_to_display:
            #     ui.markdown("###### Files & Data").classes("mt-3 text-base font-medium text-gray-700") # Enhanced heading
            #     for f_path in files_to_display:
            #         with ui.card().tight().classes("my-2 w-full shadow-md rounded-lg overflow-hidden"): # Added rounded-lg and overflow-hidden
            #             with ui.card_section().classes("flex justify-between items-center p-3 bg-slate-50 border-b"): # Slightly more padding and border
            #                 ui.label(f_path.name).classes("font-semibold text-sm text-gray-800")
            #                 ui.button(icon="download", on_click=lambda current_path=str(f_path): ui.download(current_path, filename=Path(current_path).name)) \
            #                     .props("flat dense size=sm color=primary round").tooltip("Download File")
                        
            #             if f_path.suffix.lower() in ['.csv', '.tsv']:
            #                 # This div will handle the horizontal scrolling for the table
            #                 with ui.element('div').classes('w-full overflow-auto'): # overflow-auto handles both x and y if needed
            #                     try:
            #                         df_prev = pd.read_csv(f_path, sep=',' if f_path.suffix.lower() == '.csv' else '\t')
            #                         # The table itself is simple. The parent div provides scrolling.
            #                         ui.table.from_pandas(df_prev.head(5)) \
            #                             .props('dense flat bordered separator=cell') \
            #                             .style('font-size: 0.75rem; min-width: 600px;') 
            #                             # min-width on table can encourage scrollbar if content is narrower than this.
            #                             # Adjust 600px as needed or make it a percentage like '150%' if appropriate.
            #                     except Exception as e_df_prev:
            #                         logging.error(f"Error previewing table {f_path}: {e_df_prev}")
            #                         with ui.card_section().classes("p-2"): # Add section for error message
            #                             ui.label(f"Preview failed for {f_path.name}: {str(e_df_prev)[:100]}").classes('text-orange-500 text-xs')
                        
            #             elif f_path.suffix.lower() == '.html':
            #                 with ui.card_section().classes("p-1 border-t"): # Added border-t
            #                     try:
            #                         with open(f_path, 'r', encoding='utf-8') as f_html_content:
            #                             html_content_str = f_html_content.read()
            #                         ui.html(html_content_str).classes('max-h-96 h-[350px] overflow-auto border w-full rounded') # Added rounded
            #                     except Exception as e_html_display:
            #                         logging.error(f"Error displaying HTML {f_path}: {e_html_display}")
            #                         ui.label(f"HTML display failed for {f_path.name}: {e_html_display}").classes('text-orange-500 text-xs p-2')
            # --- Display Files (with conditional preview for CSV/TSV) ---
            files_to_display = [self.outputs_dir / f for f in files_raw if f and isinstance(f, (str, Path)) and (self.outputs_dir / f).is_file()]
            if files_to_display:
                ui.markdown("###### Files & Data").classes("mt-3 text-base font-medium text-gray-700")
                for f_path in files_to_display:
                    # Check if the file is a CSV or TSV
                    if f_path.suffix.lower() in ['.csv', '.tsv']:
                        # --- Logic for CSV/TSV files (with preview) ---
                        with ui.card().tight().classes("my-2 w-full shadow-md rounded-lg overflow-hidden"):
                            # Header with filename and download button
                            with ui.card_section().classes("flex justify-between items-center p-3 bg-slate-50 border-b"):
                                ui.label(f_path.name).classes("font-semibold text-sm text-gray-800")
                                ui.button(icon="download", on_click=lambda current_path=str(f_path): ui.download(current_path, filename=Path(current_path).name)) \
                                    .props("flat dense size=sm color=primary round").tooltip("Download File")
                            
                            # Container for the table preview
                            with ui.element('div').classes('w-full overflow-auto'):
                                try:
                                    df_prev = pd.read_csv(f_path, sep=',' if f_path.suffix.lower() == '.csv' else '\t')
                                    # Display the preview table
                                    ui.table.from_pandas(df_prev.head(5)) \
                                        .props('dense flat bordered separator=cell') \
                                        .style('font-size: 0.75rem; min-width: 600px;')
                                except Exception as e_df_prev:
                                    logging.error(f"Error previewing table {f_path}: {e_df_prev}")
                                    with ui.card_section().classes("p-2"):
                                        ui.label(f"Preview failed for {f_path.name}").classes('text-orange-500 text-xs')
                    else:
                        # --- Logic for ALL OTHER file types (download only) ---
                        with ui.card().tight().classes("my-2 w-full shadow-md rounded-lg"):
                            with ui.card_section().classes("flex justify-between items-center p-3 bg-slate-50"):
                                ui.label(f_path.name).classes("font-semibold text-sm text-gray-800")
                                ui.button(icon="download", on_click=lambda current_path=str(f_path): ui.download(current_path, filename=Path(current_path).name)) \
                                    .props("flat dense size=sm color=primary round").tooltip("Download File")
            # if source_data.get("cost") is not None:
            #     ui.markdown(f"**API cost for this query:** ${source_data['cost']:.4f}") \
            #     .classes("mt-3 text-sm text-gray-600")

            # --- Fallback message if no content to display ---
            if not plots_to_display and not files_to_display and \
               not (formatted_middle_steps_str and not formatted_middle_steps_str.startswith("*No")):
                ui.label("No specific plots, files, or detailed agent workings for this message.").classes("m-4 text-gray-500 italic text-center")
    
    def update_chat_display(self):
        if not self.chat_container:
            logging.warning("Chat container not available for update_chat_display.")
            return
        
        self.chat_container.clear()
        with self.chat_container:
            for i, msg_data in enumerate(self.messages):
                role, is_user = msg_data.get("role", "assistant"), msg_data.get("role") == "user"
                name = self.user_id if is_user else "Agent"
                # avatar_char = "name[0].upper() if name else ('U' if is_user else 'A')"
                
                chat_message_props = (
                    f"text-color=black bg-color={'blue-1' if is_user else 'grey-2'} "
                    f"name-color={'indigo-8' if is_user else 'deep-purple-8'}"
                )
                
                with ui.chat_message(
                    name=name, 
                    sent=is_user, 
                    avatar='/static/user.png' if is_user else '/static/agent.png'
                ).props(chat_message_props).classes('w-full rounded-lg shadow-sm'):
                    
                    with ui.column().classes('w-full no-wrap pa-0 ma-0'): 
                        original_content_value = msg_data.get("content", "")
                        msg_type = msg_data.get("type", "text") # type includes "text_with_attachments", "text_with_candidates"
                        
                        final_content_for_markdown: str
                        if isinstance(original_content_value, list):
                            final_content_for_markdown = "\\n".join(map(str, original_content_value)) # Use \\n for markdown newlines
                        else:
                            final_content_for_markdown = str(original_content_value)
                        
                        ui.markdown(final_content_for_markdown).classes('text-sm link-styling')

                        # Custom client-side timestamp rendering
                        raw_timestamp_str = msg_data.get("timestamp")
                        if raw_timestamp_str and isinstance(raw_timestamp_str, str) and raw_timestamp_str.strip():
                            timestamp_dom_id = f"custom_ts_element_{uuid.uuid4().hex[:8]}"
                            ui.html(f'<div id="{timestamp_dom_id}" class="custom-timestamp-style w-full text-right"></div>')

                            js_code_to_format_stamp = f"""
                                (function() {{
                                    var el = document.getElementById('{timestamp_dom_id}');
                                    var utcTimestampStr = '{raw_timestamp_str}';
                                    if (el) {{
                                        try {{
                                            var date = new Date(utcTimestampStr);
                                            if (!isNaN(date.getTime())) {{
                                                el.textContent = date.toLocaleTimeString(undefined, {{ hour: 'numeric', minute: '2-digit', hour12: true }});
                                            }} else {{ el.textContent = ''; }}
                                        }} catch (e) {{ el.textContent = ''; }}
                                    }}
                                }})();
                            """
                            ui.timer(0.15, lambda code=js_code_to_format_stamp: ui.run_javascript(code), once=True)

                        # Buttons for assistant messages
                        if role == "assistant":
                            with ui.row().classes("items-center -ml-1 mt-1 gap-x-1"): # Action buttons row
                                has_details_content = (
                                    bool(msg_data.get("plots")) or 
                                    bool(msg_data.get("files")) or
                                    (msg_data.get("middle_steps") and not str(msg_data.get("middle_steps")).startswith("*No"))
                                )
                                if has_details_content:
                                    ui.button("View Details", icon="table_chart", on_click=lambda bound_idx=i: self.show_details_for_message(bound_idx))\
                                        .props('flat color=teal rounded size=sm').classes('text-xs px-2 py-0.5')
                                
                                if not msg_data.get('bookmarked'):
                                    ui.button(icon="bookmark_add", on_click=lambda msg_idx=i: self.add_bookmark(msg_idx))\
                                        .props("flat dense round color=amber-8 size=sm").tooltip("Bookmark this response")
                                else:
                                    ui.icon("bookmark_added", color="amber-8 size-5").classes("ml-1 cursor-default").tooltip("Bookmarked")
                            
                            # Display candidate solutions if present (example structure)
                            if msg_type == "text_with_candidates" and msg_data.get("candidates"):
                                for cand_idx, cand in enumerate(msg_data.get("candidates", [])):
                                    with ui.expansion(f"Candidate {cand_idx+1}: {cand.get('option', 'Option')}", icon='ballot').classes('w-full my-1 text-xs shadow-sm rounded-md border'):
                                        ui.markdown(f"**Expl:** {cand.get('explanation', '')[:150]}...").classes("p-1")
                                        if self.chat_input_field: 
                                            ui.button("Use this", icon='check_circle_outline', 
                                                      on_click=lambda c=cand, ci=self.chat_input_field: (
                                                          ci.set_value(f"Regarding candidate '{c.get('option','')}': {c.get('explanation','')}... Please proceed."), 
                                                          ci.run_method('focus'))
                                                      ).props(f'flat dense size=xs key="refine_{i}_{cand_idx}"').classes("m-1")
                            
                            # Display next steps suggestions
                            if msg_data.get("next_steps"):
                                with ui.row().classes("mt-2 gap-1 flex-wrap items-center"):
                                    ui.markdown("**Next:**").classes("self-center text-xs mr-1 text-gray-700")
                                    for step_idx, step in enumerate(msg_data["next_steps"][:3]): # Show up to 3
                                        if self.chat_input_field:
                                            ui.button(step, 
                                                      on_click=lambda s=step, ci=self.chat_input_field: (ci.set_value(s), ci.run_method('focus'))) \
                                                .props(f'flat dense no-caps key="next_step_{i}_{step_idx}"') \
                                                .classes('text-sm bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-full px-3 py-1')
        
        # Scroll to bottom logic
        def scroll_chat_to_bottom_js():
            if self.chat_container and self.chat_container.client.has_socket_connection:
                chat_id = self.chat_container.id
                js_command = f"var el = getElement({chat_id}); if (el) {{ el.scrollTop = el.scrollHeight; }}"
                ui.run_javascript(js_command)
        ui.timer(0.1, scroll_chat_to_bottom_js, once=True)
        
    def _handle_drawer_escape_key(self, e):
        try:
            key_obj = getattr(e, 'key', None)
            action_obj = getattr(e, 'action', None)
            is_escape = False
            if key_obj:
                if hasattr(key_obj, 'escape') and key_obj.escape is True: is_escape = True
                elif hasattr(key_obj, 'name') and isinstance(key_obj.name, str) and key_obj.name.lower() == 'escape': is_escape = True
            is_keydown = False
            if action_obj and hasattr(action_obj, 'keydown') and action_obj.keydown is True: is_keydown = True
            if is_escape and is_keydown:
                if self.left_drawer and self.left_drawer.value: self.left_drawer.value = False
        except AttributeError: pass


# --- CLI Argument Parsing & App Run ---
if __name__ in {"__main__", "__mp_main__"}:
    parser = argparse.ArgumentParser(description="Galaxy Chat Analysis with DSPy and NiceGUI")
    parser.add_argument("--user_id", nargs='?', default=f"user_{uuid.uuid4().hex[:6]}", help="User ID (defaults to a random ID).")
    parser.add_argument("--openai_key_file", dest="cli_openai_key_file_path", help="Path to OpenAI API key file.")
    parser.add_argument("--groq_key_file", dest="cli_groq_key_file_path", help="Path to Groq API key file.")
    parser.add_argument("--chat_history", dest="chat_history_path", default=str(DEFAULT_CHAT_HISTORY_FILE), help="Path to chat history JSON file.")
    parser.add_argument("--outputs_dir", dest="generate_file_path", default=str(DEFAULT_outputs_dir), help="Directory for generated files (plots, data).")
    parser.add_argument("--input_file", dest="input_file_path", help="Path to an initial dataset file to load.")
    parser.add_argument("--input_type", dest="input_data_type", default="csv", help="Type of the initial dataset file (e.g., csv, tsv, h5ad).")
    parser.add_argument("--dspy_examples", dest="dspy_examples_path", default=str(DEFAULT_DSPY_EXAMPLES_FILE), help="Path to DSPy training examples JSON file.")
    parser.add_argument("--compile_dspy", dest="compile_dspy_agent", action=argparse.BooleanOptionalAction, default=True, help="Enable/disable DSPy agent compilation on startup.")
    parser.add_argument("--file_name", dest="file_name", default=None, help="Optional file name to use for the initial dataset (if provided).")


    cli_args = parser.parse_args()

    parsed_outputs_dir = Path(cli_args.generate_file_path)

    # Ensure output directory exists
    Path(cli_args.generate_file_path).mkdir(parents=True, exist_ok=True)
    (Path(cli_args.generate_file_path) / AGENT_GENERATED_FILES_SUBDIR).mkdir(parents=True, exist_ok=True)

    # dspy_cache_path = parsed_outputs_dir / ".dspy_cache"
    # dspy_cache_path.mkdir(parents=True, exist_ok=True)
    # os.environ["DSPY_CACHE_DIR"] = str(dspy_cache_path)
    # logging.info(f"DSPY_CACHE_DIR explicitly set to: {dspy_cache_path.resolve()}")

    # # Configure Matplotlib cache directory
    # matplotlib_cache_path = parsed_outputs_dir / ".matplotlib_cache"
    # matplotlib_cache_path.mkdir(parents=True, exist_ok=True)
    # os.environ["MPLCONFIGDIR"] = str(matplotlib_cache_path)
    # logging.info(f"MPLCONFIGDIR explicitly set to: {matplotlib_cache_path.resolve()}")

    app_instance = NiceGuiApp(user_id=cli_args.user_id, cli_args_ns=cli_args)

    @ui.page('/')
    def main_page_entry(client: Client): # client arg is passed by NiceGUI
        app_instance.build_ui()

    app.add_static_files('/static', SCRIPT_PATH / 'static')

    ui.run(title="Galaxy Chat Analysis (DSPy)", storage_secret=str(uuid.uuid4()),
           port=9090, reload=True, # Check env var for reload
           uvicorn_logging_level='info',
           favicon=SCRIPT_PATH / "static" / "favicon.ico",)
