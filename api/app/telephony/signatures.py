"""Bounded Twilio request-signature verification."""

from collections import defaultdict
from collections.abc import Mapping, Sequence

from twilio.request_validator import RequestValidator

type TwilioParameters = Mapping[str, str] | Sequence[tuple[str, str]]


class _TwilioMultiDict:
    """Preserve every form pair for Twilio's supported validator."""

    def __init__(self, pairs: Sequence[tuple[str, str]]) -> None:
        self._values: defaultdict[str, list[str]] = defaultdict(list)
        for name, value in pairs:
            self._values[name].append(value)

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter(self._values)

    def getall(self, name: str) -> list[str]:
        return self._values.get(name, [])


def _parameters(parameters: TwilioParameters) -> Mapping[str, str] | _TwilioMultiDict:
    if isinstance(parameters, Mapping):
        return parameters
    return _TwilioMultiDict(parameters)


def twilio_signature(url: str, parameters: TwilioParameters, auth_token: str) -> str:
    """Produce a test signature through Twilio's supported SDK validator."""

    return RequestValidator(auth_token).compute_signature(url, _parameters(parameters))


def verify_twilio_signature(
    url: str,
    parameters: TwilioParameters,
    signature: str | None,
    auth_token: str,
) -> bool:
    if not signature or not auth_token:
        return False
    return RequestValidator(auth_token).validate(url, _parameters(parameters), signature)
