"""Optional, observational progress; delivery must never stop inference."""
import copy
import logging


def publish(observer, stage, **details):
    if observer is None:
        return
    try:
        observer(stage, copy.deepcopy(details))
    except Exception:
        logging.getLogger(__name__).warning('Progress delivery failed; inference continues.', exc_info=True)
