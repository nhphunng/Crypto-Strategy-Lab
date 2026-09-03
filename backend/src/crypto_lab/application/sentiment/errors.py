"""Failures shared by the sentiment service and its model adapters."""


class SentimentModelUnavailable(RuntimeError):
    """A deployment/model failure: leave articles pending for the next cycle."""
