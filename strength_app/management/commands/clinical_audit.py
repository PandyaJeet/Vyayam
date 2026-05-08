"""
Django management command: python manage.py clinical_audit

Dispatches to the clinical audit runner in strength_app/tests/clinical_audit/core/runner.py.

Usage examples:
  python manage.py clinical_audit --agent orchestrator_selftest
  python manage.py clinical_audit --agent 1_strength_gen --n 2000 --seed 42
  python manage.py clinical_audit --agent 4_football_scoring_oracle \\
      --against-cases reports/agent2_cases.jsonl,reports/agent3_cases.jsonl
  python manage.py clinical_audit --agent 7_coverage_watcher \\
      --read reports/agent1_cases.jsonl,reports/agent2_cases.jsonl,reports/agent3_cases.jsonl
"""

import sys
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Run a clinical audit agent against the VYAYAM prescription engine."

    def add_arguments(self, parser):
        parser.add_argument(
            "--agent",
            required=True,
            help="Agent ID to run (e.g. orchestrator_selftest, 1_strength_gen, …).",
        )
        parser.add_argument(
            "--n",
            type=int,
            default=500,
            help="Number of synthetic cases to generate (default: 500).",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Random seed for deterministic generation (default: 42).",
        )
        parser.add_argument(
            "--against-cases",
            dest="against_cases",
            default="",
            help="Comma-separated JSONL files of cases to run oracles against.",
        )
        parser.add_argument(
            "--read",
            default="",
            help="Comma-separated JSONL files for watchers to read.",
        )

    def handle(self, *args, **options):
        from strength_app.tests.clinical_audit.core.runner import run, AGENT_REGISTRY

        agent_id = options["agent"]

        if agent_id not in AGENT_REGISTRY:
            raise CommandError(
                f"Unknown agent {agent_id!r}.\n"
                f"Available agents: {', '.join(sorted(AGENT_REGISTRY))}"
            )

        self.stdout.write(f"Running clinical audit agent: {agent_id}")

        try:
            exit_code = run(
                agent_id=agent_id,
                n=options["n"],
                seed=options["seed"],
                against_cases=options["against_cases"],
                read=options["read"],
            )
        except NotImplementedError as e:
            raise CommandError(str(e))
        except Exception as e:
            raise CommandError(f"Agent {agent_id!r} failed: {e}") from e

        if exit_code != 0:
            sys.exit(exit_code)

        self.stdout.write(self.style.SUCCESS(f"Agent {agent_id!r} completed successfully."))
