# This file contains sufficient typing annotations for flask to make
# mypy happy.

import logging
from typing import Any, Callable, Optional, TypeVar, cast

TFunc = TypeVar("TFunc", bound=Callable[..., Any])

class Config(dict[str, str]):
    def from_mapping(self, mapping: dict[str, str]) -> None: ...

class Flask:
    logger: logging.Logger
    config: Config
    def __init__(self, name: str) -> None: ...
    def route(
        self, path: str, methods: Optional[list[str]] = None
    ) -> Callable[[TFunc], TFunc]: ...
    def after_request(self, func: TFunc) -> Callable[[TFunc], TFunc]: ...

class Response:
    headers: dict[str, str]
    def __init__(self, data: str, **kwargs: Any) -> None: ...

class Request:
    headers: dict[str, str]
    json: dict[str, str]

def send_from_directory(dir: str, path: str) -> Response: ...

response: Response
request: Request
current_app: Flask
