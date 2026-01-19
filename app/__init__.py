import warnings
import os

# Suppress annoying startup warnings from Pydantic and LlamaIndex
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore", message=".*validate_default.*")
warnings.filterwarnings("ignore", category=FutureWarning, module="llama_index")
warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")

# Set environment variable to suppress some C++ logs if any
os.environ["GRPC_VERBOSITY"] = "ERROR"
os.environ["GLOG_minloglevel"] = "2"
