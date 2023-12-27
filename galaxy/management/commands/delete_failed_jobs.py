# Source: https://gist.github.com/jbarham/de89f85e900bf5f3adce3f0e4d65c5d9
from django.core.management.base import BaseCommand
from django_rq.queues import get_queue
from django_rq.utils import get_jobs
from rq.registry import FailedJobRegistry


class Command(BaseCommand):
    help = "Delete failed jobs from Django RQ."

    def add_arguments(self, parser):
        parser.add_argument("-q", "--queue", default="default", help="queue name (default: 'default')")
        parser.add_argument("-f", "--func", help="optional job function name, e.g. 'app.tasks.func'")
        parser.add_argument("--dry-run", action="store_true", help="Do not actually delete failed jobs")

    def handle(self, *args, **options):
        queue = get_queue(options["queue"])
        registry = FailedJobRegistry(queue.name, queue.connection)
        job_ids = registry.get_job_ids()
        jobs = get_jobs(queue, job_ids, registry)
        func_name = options.get("func")
        if func_name:
            jobs = [job for job in jobs if job.func_name == func_name]
        if options["dry_run"]:
            print(f"Found {len(jobs)} failed jobs")
        else:
            for job in jobs:
                queue.connection.lrem(queue.key, 0, job.id)
                job.delete()
            print(f"Deleted {len(jobs)} failed jobs")
