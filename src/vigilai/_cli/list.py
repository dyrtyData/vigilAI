import typer
from inspect_ai import TaskInfo
from rich import print

from vigilai._cli.utils import get_vigilai_tasks
from vigilai.brazil.mapping import brazil_article_for


def _brazil_metadata(task: TaskInfo) -> tuple[str | None, str | None]:
    """Resolve a task's Brazil article/scope.

    Prefers the ``brazil_article`` / ``brazil_scope`` decorator kwargs (exposed via
    ``TaskInfo.attribs``); falls back to deriving them from the task's
    ``technical_requirement`` via the canonical mapping so EU-only tasks that predate the
    Brazil tagging still resolve correctly.
    """
    article = task.attribs.get("brazil_article")
    scope = task.attribs.get("brazil_scope")
    if article is not None:
        return article, scope

    mapped = brazil_article_for(task.attribs.get("technical_requirement", ""))
    if mapped is not None:
        return mapped
    return None, None


def _list_by_technical_requirement(tasks: list[TaskInfo]) -> None:
    """Group tasks by EU technical requirement (default view), annotating Brazil mapping."""
    tasks_by_requirement: dict[str, list[TaskInfo]] = {}
    for task in tasks:
        requirement = task.attribs["technical_requirement"]
        tasks_by_requirement.setdefault(requirement, []).append(task)

    for requirement, requirement_tasks in tasks_by_requirement.items():
        article, scope = _brazil_metadata(requirement_tasks[0])
        if article is not None:
            scope_suffix = f" / {scope}" if scope else ""
            brazil = f"[cyan]→ Brazil {article}{scope_suffix}[/cyan]"
        else:
            brazil = "[dim]→ no Brazil mapping[/dim]"
        print(f"[bold]{requirement}[/bold] {brazil}")
        print("  " + ",".join(task.name for task in requirement_tasks))


def _list_by_brazil_article(tasks: list[TaskInfo]) -> None:
    """Group tasks by Brazil PL 2338/2023 article (``--brazil`` view)."""
    tasks_by_article: dict[str, list[TaskInfo]] = {}
    scope_by_article: dict[str, str | None] = {}
    unmapped: list[TaskInfo] = []
    for task in tasks:
        article, scope = _brazil_metadata(task)
        if article is None:
            unmapped.append(task)
            continue
        tasks_by_article.setdefault(article, []).append(task)
        scope_by_article[article] = scope

    print("[bold]Brazil PL 2338/2023 — tasks grouped by article[/bold]\n")
    for article in sorted(tasks_by_article):
        scope = scope_by_article.get(article)
        scope_suffix = f" [cyan]({scope})[/cyan]" if scope else ""
        print(f"[bold]{article}[/bold]{scope_suffix}")
        print("  " + ",".join(task.name for task in tasks_by_article[article]))

    if unmapped:
        print(
            f"\n[dim]No Brazil mapping ({len(unmapped)} EU-only tasks):[/dim]"
        )
        print("  [dim]" + ",".join(task.name for task in unmapped) + "[/dim]")


def list_command(
    brazil: bool = typer.Option(
        False,
        "--brazil",
        help="Group tasks by Brazil PL 2338/2023 article instead of EU technical requirement.",
    ),
) -> None:
    """List all available tasks.

    By default tasks are grouped by EU technical requirement (the COMPL-AI taxonomy),
    annotated with their Brazil PL 2338/2023 article mapping where one exists. Pass
    ``--brazil`` to group by Brazil article instead.
    """
    tasks = get_vigilai_tasks()
    if not tasks:
        print("No tasks available.")
        return

    if brazil:
        _list_by_brazil_article(tasks)
    else:
        _list_by_technical_requirement(tasks)
