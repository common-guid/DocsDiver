"""Command-line entry point for offline evaluation preparation."""

import argparse
from pathlib import Path
import sys


def _problems(problems):
    for problem in problems:
        print(problem, file=sys.stderr)
    return 1


def _verify(args):
    from . import corpus

    problems = corpus.verify(args.dir)
    if problems:
        return _problems(problems)
    digest, count = corpus.tree_hash(args.dir)
    print(f"OK {count} files, tree {digest}")
    return 0


def _check(args):
    from . import key

    data = key.load(args.key)
    problems = key.check(data, args.clean)
    if problems:
        return _problems(problems)
    print(f"OK {data['key_id']} v{data['key_version']} sha256 {key.key_hash(args.key)}, {len(data['items'])} items")
    return 0


def _build(args):
    import yaml
    from . import corpus, key

    data = key.load(args.key)
    problems = key.check(data, args.clean)
    if problems:
        return _problems(problems)
    edits = key.approved_edits(data)
    if not edits:
        return _problems(["no approved plants"])
    try:
        variants = corpus.build(args.clean, args.seeded, edits)
    except corpus.CorpusError as exc:
        return _problems(exc.problems)
    path = Path(args.variants) if args.variants else Path(args.key).parent / "variants.yaml"
    plants = list(dict.fromkeys(edit[0] for edit in edits))
    record = {"snapshot_id": data["snapshot_id"], "key_id": data["key_id"],
              "key_hash": key.key_hash(args.key), "plants": plants, "variants": variants}
    path.write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")
    print(f"OK clean {variants['clean']['tree_hash']} seeded {variants['seeded']['tree_hash']}, {len(plants)} plants -> {path}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m evals")
    commands = parser.add_subparsers(dest="command", required=True)
    corpus = commands.add_parser("corpus").add_subparsers(dest="action", required=True)
    verify = corpus.add_parser("verify")
    verify.add_argument("dir")
    verify.set_defaults(handler=_verify)
    build = corpus.add_parser("build")
    for name in ("key", "clean", "seeded"):
        build.add_argument(f"--{name}", required=True)
    build.add_argument("--variants")
    build.set_defaults(handler=_build)
    check = commands.add_parser("key").add_subparsers(dest="action", required=True).add_parser("check")
    check.add_argument("--key", required=True)
    check.add_argument("--clean", required=True)
    check.set_defaults(handler=_check)
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except (OSError, ValueError) as exc:
        return _problems([str(exc)])


if __name__ == "__main__":
    sys.exit(main())
