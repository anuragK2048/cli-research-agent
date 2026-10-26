import inspect
from typing import Callable


class Tool:
    def __init__(self, name: str, description: str, func: Callable, arguments: list, outputs: str):
         self.name = name
         self.description = description
         self.func = func
         self.arguments = arguments
         self.outputs = outputs

    def to_string(self):
        """
        Return a string representation of the tool,
        including its name, description, arguments, and outputs.
        """
        args_str = ", ".join([f"{arg_name}: {arg_type}" for arg_name, arg_type in self.arguments])
        return (
            f"Tool Name: {self.name},"
            f" Description: {self.description},"
            f" Arguments: {args_str},"
            f" Outputs: {self.outputs}"
        )

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


def tool(func):
    """
    A decorator that creates a Tool instance from the given function.
    """
    # Get the function signature
    signature = inspect.signature(func)

    # get args
    args = []
    for param in signature.parameters.values():
        annotation_name = (
            param.annotation.__name__
            if hasattr(param.annotation, '__name__')
            else str(param.annotation)
        )
        args.append((param.name, annotation_name))

    # get return type
    return_annotation = signature.return_annotation
    if return_annotation is inspect._empty:
        outputs = "No return annotation"

    else:
        outputs = (
            return_annotation.__name__
            if hasattr(return_annotation, '__name__')
            else str(return_annotation)
        )

    description = func.__doc__ or "No description provided."

    name = func.__name__

    return Tool(
        name = name,
        description = description,
        func = func,
        arguments = args,
        outputs = outputs
    )

# @tool
# def web_search(url: str, max_results: int = 5) -> str:
#     """Lists web pages related to particular query"""
#     print(f"Web search performed for query: {url} with max result {max_results}")
#     return "Web search results"

