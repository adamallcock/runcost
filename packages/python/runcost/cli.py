from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union

from .core import (
    aggregate_cost_ledgers,
    calculate_cost,
    from_response,
    price_cards_from_helicone,
    price_cards_from_json_file,
    price_cards_from_litellm,
    price_cards_from_llm_prices,
    price_cards_from_models_dev,
    price_cards_from_official_snapshot,
    price_cards_from_openrouter_models,
    price_cards_from_portkey,
    price_cards_from_source_cache,
    price_cards_from_user_pricing,
    price_cards_from_yaml_file,
)
from .expansion import canonical_json_bytes, from_batch_results, verify_catalog_manifest
from .price_resolver import (
    DEFAULT_EXTERNAL_PRICE_SOURCES,
    clear_price_cache,
    from_batch_results_auto,
    from_response_auto,
    price_cache_status,
    resolve_price_catalog,
)


def _load_json(path: Union[str, Path]) -> Any:
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def _write_json(data: Any, output: Optional[str]) -> None:
    text = json.dumps(data, indent=2, sort_keys=True) + "\n"
    if output:
        Path(output).write_text(text, encoding="utf-8")
        return
    sys.stdout.write(text)


def _write_canonical_json(data: Any, output: Optional[str]) -> None:
    encoded = canonical_json_bytes(data)
    if output:
        Path(output).write_bytes(encoded)
        return
    sys.stdout.buffer.write(encoded)


def _read_quote_input(path: Optional[str], force_jsonl: bool = False) -> tuple[List[Any], bool]:
    if path in (None, "-"):
        text = sys.stdin.read()
    else:
        text = Path(path).read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError("quote input is empty")
    if not force_jsonl:
        try:
            value = json.loads(text)
            if isinstance(value, list):
                return value, True
            return [value], False
        except json.JSONDecodeError:
            pass
    values = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            values.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at line {line_number}: {exc.msg}") from exc
    if not values:
        raise ValueError("quote input contains no JSON objects")
    return values, True


def _price_cards_from_source(source_type: str, data: Any, input_path: Optional[str] = None) -> List[Dict[str, Any]]:
    if source_type == "llm-prices":
        return price_cards_from_llm_prices(data)
    if source_type == "litellm":
        return price_cards_from_litellm(data)
    if source_type == "openrouter-models":
        return price_cards_from_openrouter_models(data)
    if source_type == "models-dev":
        return price_cards_from_models_dev(data)
    if source_type == "official-snapshot":
        return price_cards_from_official_snapshot(data)
    if source_type == "portkey":
        return price_cards_from_portkey(data)
    if source_type == "source-cache":
        return price_cards_from_source_cache(data)
    if source_type == "user-pricing":
        return price_cards_from_user_pricing(data)
    if source_type == "helicone":
        return price_cards_from_helicone(data)
    if source_type == "json-file":
        if not input_path:
            raise ValueError("json-file source requires --input")
        return price_cards_from_json_file(Path(input_path), "user-pricing")
    if source_type == "yaml-file":
        if not input_path:
            raise ValueError("yaml-file source requires --input")
        return price_cards_from_yaml_file(Path(input_path), "user-pricing")
    raise ValueError(f"unsupported source type: {source_type}")


def _resolve_fixture_price_cards(fixture: Dict[str, Any]) -> List[Dict[str, Any]]:
    input_data = fixture.get("input", {})
    if "price_cards" in input_data:
        return input_data["price_cards"]
    source = input_data.get("price_source")
    if isinstance(source, dict):
        if "data" in source:
            return _price_cards_from_source(source["type"], source["data"])
        if "path" in source:
            return _price_cards_from_source(source["type"], _load_json(source["path"]), source["path"])
    return []


def _fixture_result(fixture: Dict[str, Any]) -> Dict[str, Any]:
    input_data = fixture["input"]
    options = {
        **input_data.get("options", {}),
        "mode": input_data.get("mode", "compatibility"),
    }
    price_cards = _resolve_fixture_price_cards(fixture)
    discount_policies = input_data.get("discount_policies", [])

    if "cost_ledgers" in input_data:
        return aggregate_cost_ledgers(input_data["cost_ledgers"], **options)
    if "raw_response" in input_data:
        return from_response(
            input_data["raw_response"],
            **{
                **input_data.get("extract", {}),
                **options,
                "price_cards": price_cards,
                "discount_policies": discount_policies,
            },
        )
    return calculate_cost(
        usage_ledger=input_data["usage_ledger"],
        price_cards=price_cards,
        discount_policies=discount_policies,
        **options,
    )


def _assert_subset(expected: Any, actual: Any, path: str = "$") -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            raise AssertionError(f"{path}: expected object, got {type(actual).__name__}")
        for key, value in expected.items():
            if key not in actual:
                raise AssertionError(f"{path}.{key}: missing key")
            _assert_subset(value, actual[key], f"{path}.{key}")
        return
    if isinstance(expected, list):
        if expected != actual:
            raise AssertionError(f"{path}: expected {expected!r}, got {actual!r}")
        return
    if expected != actual:
        raise AssertionError(f"{path}: expected {expected!r}, got {actual!r}")


def command_price_cards(args: argparse.Namespace) -> int:
    data = _load_json(args.input)
    price_cards = _price_cards_from_source(args.source_type, data, args.input)
    _write_json(price_cards, args.output)
    return 0


def command_fixture_check(args: argparse.Namespace) -> int:
    fixture = _load_json(args.fixture)
    actual = _fixture_result(fixture)
    expected = fixture.get("expected", {}).get("cost_ledger")
    if expected is not None:
        _assert_subset(expected, actual)
    _write_json(actual, args.output)
    return 0


def _resolver_options(args: argparse.Namespace) -> Dict[str, Any]:
    options: Dict[str, Any] = {}
    if getattr(args, "price_source", None):
        options["sources"] = args.price_source
    if getattr(args, "cache_dir", None):
        options["cache_dir"] = args.cache_dir
    if getattr(args, "offline", False):
        options["offline"] = True
    if getattr(args, "refresh", False):
        options["refresh"] = True
    if getattr(args, "max_age_seconds", None) is not None:
        options["max_age_seconds"] = args.max_age_seconds
    if getattr(args, "now", None) is not None:
        options["now"] = args.now
    return options


def _quote_one(value: Any, args: argparse.Namespace) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("each quote input must be a JSON object")
    envelope = value
    response = envelope.get("raw_response", envelope.get("response", envelope))
    if not isinstance(response, dict):
        raise ValueError("quote response must be a JSON object")
    embedded_options = envelope.get("options") if isinstance(envelope.get("options"), dict) else {}
    options: Dict[str, Any] = dict(embedded_options)
    for name in ("provider", "surface", "model"):
        value_option = getattr(args, name, None)
        if value_option is not None:
            options[name] = value_option
    if isinstance(envelope.get("price_cards"), list):
        options["price_cards"] = envelope["price_cards"]
    if isinstance(envelope.get("discount_policies"), list):
        options["discount_policies"] = envelope["discount_policies"]
    if isinstance(envelope.get("attribution"), dict):
        options["attribution"] = envelope["attribution"]
    if args.no_resolve:
        return from_response(response, **options)
    return from_response_auto(response, **{**options, **_resolver_options(args)})


def command_quote(args: argparse.Namespace) -> int:
    values, multi = _read_quote_input(args.input, args.jsonl)
    if args.batch_provider:
        batch_value: Any = values
        if len(values) == 1 and isinstance(values[0], dict) and isinstance(values[0].get("items"), list):
            batch_value = values[0]["items"]
        batch_options: Dict[str, Any] = {
            "provider": args.batch_provider,
            "surface": args.surface,
            "endpoint": args.endpoint,
            "model": args.model,
            "batch_id": args.batch_id,
            **_resolver_options(args),
        }
        batch_options = {key: value for key, value in batch_options.items() if value is not None}
        result = from_batch_results(batch_value, **batch_options) if args.no_resolve else from_batch_results_auto(batch_value, **batch_options)
    else:
        quoted = [_quote_one(value, args) for value in values]
        result = quoted if multi else quoted[0]
    _write_canonical_json(result, args.output)
    return 0


def command_catalog_verify(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest)
    manifest = _load_json(manifest_path)
    result = verify_catalog_manifest(manifest, root=args.root or manifest_path.parent)
    _write_canonical_json(result, args.output)
    return 0 if result["valid"] else 1


def command_prices_refresh(args: argparse.Namespace) -> int:
    sources = args.price_source or list(DEFAULT_EXTERNAL_PRICE_SOURCES)
    resolutions = []
    succeeded = True
    for source in sources:
        resolution = resolve_price_catalog(
            sources=[source],
            cache_dir=args.cache_dir,
            refresh=True,
            max_age_seconds=args.max_age_seconds,
            now=args.now,
        )
        resolutions.append(
            {
                "source": source,
                "selected_source": resolution["selected_source"],
                "card_count": len(resolution["price_cards"]),
                "sources": resolution["sources"],
                "warnings": resolution["warnings"],
                "resolved_at": resolution["resolved_at"],
            }
        )
        succeeded = succeeded and resolution["selected_source"] == source
    _write_canonical_json({"schema_version": "0.1", "resolutions": resolutions}, args.output)
    return 0 if succeeded else 1


def command_prices_status(args: argparse.Namespace) -> int:
    _write_canonical_json(price_cache_status(cache_dir=args.cache_dir, now=args.now), args.output)
    return 0


def command_prices_clear(args: argparse.Namespace) -> int:
    _write_canonical_json(clear_price_cache(cache_dir=args.cache_dir, sources=args.price_source), args.output)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="runcost", description="RunCost package utilities.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    price_cards = subparsers.add_parser("price-cards", help="Convert a pricing source JSON file to price cards.")
    price_cards.add_argument("--source-type", required=True)
    price_cards.add_argument("--input", required=True)
    price_cards.add_argument("--output")
    price_cards.set_defaults(func=command_price_cards)

    fixture_check = subparsers.add_parser("fixture-check", help="Calculate and optionally verify one RunCost fixture.")
    fixture_check.add_argument("fixture")
    fixture_check.add_argument("--output")
    fixture_check.set_defaults(func=command_fixture_check)

    quote = subparsers.add_parser("quote", help="Price raw provider responses from JSON, JSONL, stdin, or files.")
    quote.add_argument("input", nargs="?", default="-", help="JSON/JSONL file, or - for stdin")
    quote.add_argument("--provider")
    quote.add_argument("--surface")
    quote.add_argument("--model")
    quote.add_argument("--jsonl", action="store_true", help="parse input as newline-delimited JSON")
    quote.add_argument("--price-source", action="append", choices=["genai-prices", "models.dev", "litellm", "openrouter"], help="external source order; repeat to add fallbacks")
    quote.add_argument("--cache-dir", help="external price-cache directory")
    quote.add_argument("--offline", action="store_true", help="never access the network; use cached prices only")
    quote.add_argument("--refresh", action="store_true", help="conditionally refresh external prices before quoting")
    quote.add_argument("--max-age-seconds", type=int, default=24 * 60 * 60, help="fresh-cache TTL (default: 86400)")
    quote.add_argument("--now", help="RFC 3339 clock override for reproducible cache/audit output")
    quote.add_argument("--no-resolve", action="store_true", help="disable external resolution and use only embedded price_cards")
    quote.add_argument("--batch-provider", help="unwrap a provider batch result collection")
    quote.add_argument("--endpoint", help="nested batch endpoint, when the result envelope does not contain it")
    quote.add_argument("--batch-id")
    quote.add_argument("--output")
    quote.set_defaults(func=command_quote)

    catalog_verify = subparsers.add_parser("catalog-verify", help="verify a SHA-256 catalog manifest")
    catalog_verify.add_argument("manifest")
    catalog_verify.add_argument("--root", help="artifact root; defaults to the manifest directory")
    catalog_verify.add_argument("--output")
    catalog_verify.set_defaults(func=command_catalog_verify)

    prices = subparsers.add_parser("prices", help="manage the external pricing cache")
    price_commands = prices.add_subparsers(dest="prices_command", required=True)
    prices_refresh = price_commands.add_parser("refresh", help="refresh external pricing sources")
    prices_refresh.add_argument("--price-source", action="append", choices=["genai-prices", "models.dev", "litellm", "openrouter"])
    prices_refresh.add_argument("--cache-dir")
    prices_refresh.add_argument("--max-age-seconds", type=int, default=24 * 60 * 60)
    prices_refresh.add_argument("--now", help="RFC 3339 clock override for reproducible output")
    prices_refresh.add_argument("--output")
    prices_refresh.set_defaults(func=command_prices_refresh)
    prices_status = price_commands.add_parser("status", help="inspect cached pricing metadata")
    prices_status.add_argument("--cache-dir")
    prices_status.add_argument("--now", help="RFC 3339 clock override for reproducible output")
    prices_status.add_argument("--output")
    prices_status.set_defaults(func=command_prices_status)
    prices_clear = price_commands.add_parser("clear", help="remove RunCost-managed pricing cache files")
    prices_clear.add_argument("--price-source", action="append", choices=["genai-prices", "models.dev", "litellm", "openrouter"])
    prices_clear.add_argument("--cache-dir")
    prices_clear.add_argument("--output")
    prices_clear.set_defaults(func=command_prices_clear)

    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        return args.func(args)
    except (AssertionError, ValueError, KeyError) as exc:
        print(f"runcost: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
