"""
Arquivo WSGI para PythonAnywhere
Configure o PythonAnywhere apontando este arquivo como WSGI application
"""

import sys
import os

# Ajusta o path para o diretório do projeto
project_home = os.path.dirname(os.path.abspath(__file__))
if project_home not in sys.path:
    sys.path.insert(0, project_home)

from app import app as application  # noqa: F401
