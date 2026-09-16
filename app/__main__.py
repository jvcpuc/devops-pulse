"""CLI: python -m app.pipeline [--hours 24] [--llm] [--tts] [--no-persist]"""

from __future__ import annotations

import argparse
import json

from app.config import get_settings
from app.logging_config import setup_logging
from app.pipeline import PulsePipeline


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="Executa o pipeline DevOps Pulse AI")
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--llm", action="store_true", help="Chamar Ollama")
    parser.add_argument("--tts", action="store_true", help="Chamar Kokoro")
    parser.add_argument("--no-persist", action="store_true")
    parser.add_argument("--demo", action="store_true", help="Forçar modo demo")
    parser.add_argument("--live", action="store_true", help="Forçar GitHub API (ignora DEMO_MODE)")
    args = parser.parse_args()

    settings = get_settings()
    use_demo = True if args.demo else (False if args.live else None)

    pipeline = PulsePipeline(settings)
    result = pipeline.run(
        hours=args.hours,
        with_llm=args.llm,
        with_tts=args.tts,
        persist=not args.no_persist,
        use_demo=use_demo,
    )
    print(json.dumps(result.model_dump(by_alias=True), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
