import re
import math
import inspect
import jsonpickle
from functools import wraps
from datetime import datetime, timezone
from typing import Optional, Iterator, List, Mapping, OrderedDict

DEFAULT_DATE_FORMAT = "%Y-%m-%d"


def utc_now():
    return datetime.now(timezone.utc)


def iso_datestr_to_datetime(datestr):
    if isinstance(datestr, str) and len(datestr) > 0:
        if datestr[-1] == "Z":
            return datetime.fromisoformat(datestr.replace("Z", "+00:00"))
        else:
            return datetime.fromisoformat(datestr)
    else:
        raise Exception("'{}' is not valid iso date format".format(datestr))


def _consolidate_table_keys(data) -> Iterator[List[str]]:
    """Format terminal log table to reduce noise from duplicate keys.

    Note:
        Data must be sorted.
    """
    prev_key: Optional[str] = None
    for key, *rest in data:
        if prev_key is not None and prev_key == key:
            yield ["〃", *rest]  # ditto
        else:
            yield [key, *rest]
        prev_key = key


def substitute_vars(input: str, vars: Mapping[str, str]):
    """
    Substitutes variables in input string with variables defined in var.

    For example, my-app-{ORDINAL_NUM} converts to my-app-0 if ORDINAL_NUM
    is a defined variable.
    """
    found = re.findall(r"{([^{}]*?)}", input)
    for v in found:
        if v in vars:
            input = input.replace(f"{{{v}}}", str(vars[v]))
    return input


def dir_to_py_module_path(dir: str):
    """Convert a directory path to a python module path"""

    module = dir.replace("/", ".").replace("..", ".")
    if module[0].startswith("."):
        module = module[1:]
    return module


def safe_cast(val, to_type, default=None):
    try:
        return to_type(val)
    except (ValueError, TypeError):
        return default


def filter_nulls(func, empty_null=True):
    @wraps(func)
    def _func(values):
        filtered = tuple(v for v in values if v is not None)
        if not filtered and empty_null:
            return None
        return func(filtered)

    return _func


def null_if_any(*required):
    """Decorator that makes a function return `None` if any of the `required` arguments are `None`.

    This also supports decoration with no arguments, e.g.:

        @null_if_any
        def foo(a, b): ...

    In which case all arguments are required.
    """
    f = None
    if len(required) == 1 and callable(required[0]):
        f = required[0]
        required = ()

    def decorator(func):
        if required:
            required_indices = [
                i
                for i, param in enumerate(inspect.signature(func).parameters)
                if param in required
            ]

            def predicate(*args):
                return any(args[i] is None for i in required_indices)

        else:

            def predicate(*args):
                return any(a is None for a in args)

        @wraps(func)
        def _func(*args):
            if predicate(*args):
                return None
            return func(*args)

        return _func

    if f:
        return decorator(f)

    return decorator


@null_if_any
def ensure_datetime_str(dt: str):
    """Converts timestamp string to millisecond percision if not already."""
    if dt[-1] == "Z":
        return (
            datetime.fromisoformat(dt.replace("Z", "+00:00"))
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z")
        )
    else:
        return (
            datetime.fromisoformat(dt)
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z")
        )


@null_if_any
def canonicalize(text: str):
    """Convert input text to canonical format"""
    return text.upper().strip().replace(",", "_").replace("=", "_").replace(" ", "_")


def truncate(number, digits) -> float:
    """Truncates a floating point number to"""
    # Improve accuracy with floating point operations,
    # to avoid truncate(16.4, 2) = 16.39 or truncate(-1.13, 2) = -1.12
    nbDecimals = len(str(number).split(".")[1])
    if nbDecimals <= digits:
        return number
    stepper = 10.0**digits
    return math.trunc(stepper * number) / stepper


@null_if_any
def ensure_dollars(val) -> float:
    """Truncates and roundes a floating point value to 2 decimal places."""
    return round(truncate(val, 3), 2)


@null_if_any
def ensure_date(dtstr, format=DEFAULT_DATE_FORMAT):
    """Converts input datetime string to YYYY-MM-DD format"""
    return datetime.fromisoformat(dtstr).strftime(format)


def ordered_dict_to_dict(data):
    if isinstance(data, OrderedDict):
        return dict((k, ordered_dict_to_dict(v)) for k, v in data.items())
    elif isinstance(data, list):
        return [ordered_dict_to_dict(i) for i in data]
    return data


def camel_to_snake(data):
    """
    Convert all keys in a dictionary from camelCase to snake_case.

    Args:
        data (dict): Input dictionary with camelCase keys

    Returns:
        dict: New dictionary with snake_case keys
    """

    def convert_key(key):
        result = ""
        for char in key:
            if char.isupper():
                result += "_" + char.lower()
            else:
                result += char
        return result

    if not isinstance(data, dict):
        return data

    return {
        convert_key(key): camel_to_snake(value) if isinstance(value, dict) else value
        for key, value in data.items()
    }


def datetime_converter(o):
    if isinstance(o, datetime):
        return o.isoformat()  # Convert datetime to ISO 8601 string
    raise TypeError("Type not serializable")


def sort_dict_keys(d):
    if isinstance(d, dict):
        return {
            key: sort_dict_keys(value) if isinstance(value, dict) else value
            for key, value in sorted(d.items())
        }
    elif isinstance(d, list):
        return [sort_dict_keys(item) if isinstance(item, dict) else item for item in d]
    else:
        return d


def canonicalize_dict(data):
    """
    Returns a canonical JSON representation of a dictionary.

    The JSON string uses sorted keys and compact separators, which ensures that
    the representation of the dictionary remains consistent even when key order varies.
    This function works recursively for nested dictionaries and handles lists too.
    """
    return jsonpickle.dumps(sort_dict_keys(data), unpicklable=False)
