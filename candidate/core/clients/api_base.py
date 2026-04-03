from __future__ import annotations

import inspect
import json
import logging
import types
from functools import wraps
from typing import Any, Callable, Optional, Type, TypeVar

import allure
import requests


logger = logging.getLogger(__name__)

TModel = TypeVar("TModel")


def url_join(base_url: str, path: str) -> str:
    """
    Join base URL and path without duplicating slashes.
    """
    return base_url.rstrip("/") + "/" + path.lstrip("/")


def func_parameters(method: Callable[..., Any], *args: Any, **kwargs: Any) -> dict[str, Any]:
    """
    Bind the call arguments for better Allure step params.
    """
    sig = inspect.signature(method)
    bound = sig.bind_partial(*args, **kwargs)
    # Remove `self` from params
    bound_args = {k: v for k, v in bound.arguments.items() if k != "self"}
    return bound_args


class ResponseWrapper:
    def __init__(self, response: requests.Response) -> None:
        self._response = response

        req = response.request
        logger.info(
            "REQUEST DATA: url=%s method=%s body=%s",
            req.url,
            req.method,
            self._format_request_body(req),
        )
        logger.info(
            "RESPONSE DATA: url=%s method=%s status=%s body=%s",
            req.url,
            req.method,
            response.status_code,
            self._format_response_body(response),
        )

    @staticmethod
    def _is_json_response(response: requests.Response) -> bool:
        content_type = response.headers.get("content-type", "")
        return "application/json" in content_type

    @staticmethod
    def _is_json_request(request: requests.PreparedRequest) -> bool:
        content_type = request.headers.get("content-type", "")
        return "application/json" in content_type

    def _format_request_body(self, request: requests.PreparedRequest) -> str:
        body = request.body
        if not body:
            return ""
        if isinstance(body, (bytes, bytearray)):
            try:
                body = body.decode("utf-8")
            except Exception:
                body = str(body)

        if self._is_json_request(request):
            try:
                return json.dumps(json.loads(body), indent=4)
            except Exception:
                return str(body)

        return str(body)

    def _format_response_body(self, response: requests.Response) -> str:
        if not self._is_json_response(response):
            return response.text
        try:
            return json.dumps(response.json(), indent=4)
        except Exception:
            return response.text

    @property
    def status_code(self) -> int:
        return self._response.status_code

    @property
    def text(self) -> str:
        return self._response.text

    @property
    def headers(self):
        return self._response.headers

    @property
    def request(self):
        return self._response.request

    def json(self) -> Any:
        return self._response.json()

    def to_model(self, model_type: Type[TModel]) -> TModel:
        """
        Validate the current JSON body against a Pydantic model.
        """
        # We type this as `Any` to avoid importing BaseModel directly here;
        # Pydantic v2 exposes `model_validate`.
        model_cls: Any = model_type
        return model_cls.model_validate(self.json())


class Base:
    def __init__(self, session: "HttpSession") -> None:  # noqa: F821
        self._session = session

    @property
    def session(self) -> "HttpSession":  # noqa: F821
        return self._session


def step_method(method: Callable[..., Any]) -> Callable[..., Any]:
    step_title = "API call: " + " ".join(method.__name__.title().split("_"))

    @wraps(method)
    def wrapper(*args: Any, **kwargs: Any):
        step_params = func_parameters(method, *args, **kwargs)
        with allure.step(step_title) as step:
            # Attach params for better traceability in Allure UI.
            try:
                step.params = step_params  # type: ignore[attr-defined]
            except Exception:
                pass

            logger.info("Start -> `%s`.", step_title)
            result = method(*args, **kwargs)

            if isinstance(result, ResponseWrapper):
                allure.attach(
                    result.text,
                    name="response",
                    attachment_type=allure.attachment_type.TEXT,
                )

            logger.info("Finish -> `%s`.", step_title)
        return result

    return wrapper


def step_methods(klass: type) -> type:
    """
    Automatically wrap all public instance methods with Allure/logging steps.
    """
    for key, klass_attr in klass.__dict__.items():
        if key.startswith("_"):
            continue
        if isinstance(klass_attr, types.FunctionType):
            setattr(klass, key, step_method(klass_attr))
    return klass


class HttpSession:
    """HTTP session wrapper used by API clients."""

    def __init__(self, base_url: str) -> None:
        self._session = requests.Session()
        self._base_url = base_url
        self._headers: dict[str, str] = {
            "Content-Type": "application/json",
        }

    @property
    def base_url(self) -> str:
        return self._base_url

    def _make_request(
        self,
        method: str,
        path: str,
        body: Optional[dict | str] = None,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        timeout: Optional[int] = None,
        **kwargs: Any,
    ) -> requests.Response:
        data = body if isinstance(body, str) else None
        json_body = body if isinstance(body, dict) else None
        url = url_join(self._base_url, path)
        merged_headers = {**self._headers, **(headers or {})}
        response = self._session.request(
            method=method,
            url=url,
            data=data,
            json=json_body,
            params=params,
            headers=merged_headers,
            timeout=timeout,
            **kwargs,
        )
        return response

    def get(
        self,
        path: str,
        body: Optional[dict | str] = None,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        timeout: Optional[int] = None,
        **kwargs: Any,
    ) -> requests.Response:
        return self._make_request(
            method="GET",
            path=path,
            body=body,
            params=params,
            headers=headers,
            timeout=timeout,
            **kwargs,
        )

    def post(
        self,
        path: str,
        body: Optional[dict | str] = None,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        timeout: Optional[int] = None,
        **kwargs: Any,
    ) -> requests.Response:
        return self._make_request(
            method="POST",
            path=path,
            body=body,
            params=params,
            headers=headers,
            timeout=timeout,
            **kwargs,
        )

    def put(
        self,
        path: str,
        body: Optional[dict | str] = None,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        timeout: Optional[int] = None,
        **kwargs: Any,
    ) -> requests.Response:
        return self._make_request(
            method="PUT",
            path=path,
            body=body,
            params=params,
            headers=headers,
            timeout=timeout,
            **kwargs,
        )

    def delete(
        self,
        path: str,
        body: Optional[dict | str] = None,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        timeout: Optional[int] = None,
        **kwargs: Any,
    ) -> requests.Response:
        return self._make_request(
            method="DELETE",
            path=path,
            body=body,
            params=params,
            headers=headers,
            timeout=timeout,
            **kwargs,
        )

