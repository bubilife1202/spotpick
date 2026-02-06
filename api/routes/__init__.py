"""FastAPI route package.

Keep this module import-light.

Importing submodules (e.g. `api.routes.competitive`) will first import this package,
so heavy imports here can unintentionally import legacy routes and trigger side effects.
"""

__all__: list[str] = []
