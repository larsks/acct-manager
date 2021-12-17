# This file contains sufficient typing annotations for flask to make
# mypy happy.

import logging
from typing import Any, Callable, TypeVar, cast

TFunc = TypeVar("TFunc", bound=Callable[..., Any])

class Config(dict[str, str]):
    def from_mapping(self, mapping: dict[str, str]) -> None: ...

class Flask:
    logger: logging.Logger
    config: Config
    def __init__(self, name: str) -> None: ...
    def route(self, path: str, methods: list[str]) -> Callable[[TFunc], TFunc]: ...

class Response:
    def __init__(self, data: str, **kwargs: Any) -> None: ...

class request:
    json: dict[str, str]

current_app: Flask
