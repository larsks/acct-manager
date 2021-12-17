# This file contains sufficient typing annotations for flask_httpauth to make
# mypy happy.

from typing import Any, Callable, TypeVar

TFunc = TypeVar("TFunc", bound=Callable[..., Any])

class HTTPBasicAuth:
    def verify_password(self, func: TFunc) -> TFunc: ...
    def login_required(self, func: TFunc) -> TFunc: ...
